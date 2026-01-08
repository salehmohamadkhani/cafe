from __future__ import annotations

import os
import re
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from datetime import datetime
import pytz

from models.models import db, Settings, User


_SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def normalize_slug(value: str) -> str:
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = value.strip('-')
    value = re.sub(r'-{2,}', '-', value)
    return value


def validate_slug(slug: str) -> bool:
    return bool(slug and _SLUG_RE.match(slug))


@dataclass(frozen=True)
class ProvisionedTenant:
    name: str
    slug: str
    root_dir: str
    db_path: str


def provision_tenant(tenants_dir: str, name: str, slug: str, source_project_dir: str = None) -> ProvisionedTenant:
    """
    Creates a complete cafe project (full copy of source project) + fresh sqlite db.
    Returns filesystem paths. Does NOT register anything in master DB.
    """
    if not tenants_dir:
        raise ValueError("tenants_dir is required")

    name = (name or '').strip()
    if not name:
        raise ValueError("name is required")

    slug = normalize_slug(slug or name)
    if not validate_slug(slug):
        raise ValueError("slug is invalid (use a-z, 0-9, dash)")

    root_dir = os.path.join(tenants_dir, slug)
    
    # If already exists, raise error
    if os.path.exists(root_dir):
        raise ValueError(f"Tenant directory already exists: {root_dir}")

    # Copy entire project structure from source
    if source_project_dir and os.path.exists(source_project_dir):
        import shutil
        
        # Directories/files to exclude when copying
        exclude_patterns = {
            '.git', '__pycache__', '*.pyc', 'venv', '.venv',
            'instance/*.db', 'instance/secret_key', 'tenants',
            '*.log', '.autopush.lock'
        }
        
        def should_exclude(path: str) -> bool:
            path_lower = path.lower()
            for pattern in exclude_patterns:
                if pattern in path_lower or path.endswith(pattern.replace('*', '')):
                    return True
            return False
        
        def copy_tree(src: str, dst: str):
            os.makedirs(dst, exist_ok=True)
            for item in os.listdir(src):
                # Skip hidden files/dirs and excluded items
                if item.startswith('.') and item not in ['.gitignore']:
                    continue
                
                src_path = os.path.join(src, item)
                dst_path = os.path.join(dst, item)
                
                # Skip specific directories
                if item in ['tenants', '.git', 'venv', '.venv', '__pycache__']:
                    continue
                
                if should_exclude(src_path):
                    continue
                
                if os.path.isdir(src_path):
                    copy_tree(src_path, dst_path)
                else:
                    # Skip specific files
                    if item.endswith(('.pyc', '.log', '.lock')) or item in ['secret_key']:
                        continue
                    if 'instance' in src_path and (item.endswith('.db') or item == 'secret_key'):
                        continue
                    shutil.copy2(src_path, dst_path)
        
        copy_tree(source_project_dir, root_dir)
        
        # Clean up instance directory completely (we'll create fresh DB)
        instance_dir = os.path.join(root_dir, 'instance')
        if os.path.exists(instance_dir):
            import shutil
            try:
                # Remove entire instance directory to ensure no old DB files are copied
                shutil.rmtree(instance_dir, ignore_errors=True)
            except:
                pass
            # Recreate empty instance directory
            os.makedirs(instance_dir, exist_ok=True)
    else:
        # Fallback: just create basic structure
        instance_dir = os.path.join(root_dir, 'instance')
        os.makedirs(instance_dir, exist_ok=True)

    instance_dir = os.path.join(root_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)

    db_path = os.path.join(instance_dir, 'cafe.db')
    db_uri = f"sqlite:///{db_path}"

    # Create schema for tenant database using existing tenant models metadata
    engine = create_engine(db_uri, future=True)
    db.metadata.create_all(bind=engine)
    
    # Clear ALL data from ALL tables to ensure completely fresh start
    # We'll create Settings and User after clearing
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        # Disable foreign key constraints temporarily
        s.execute(text("PRAGMA foreign_keys=OFF"))
        
        # Delete all data from ALL tables (comprehensive list)
        # Order matters: delete child tables first, then parent tables
        all_tables_to_clear = [
            # Child tables with foreign keys (delete first)
            'order_item',
            'table_item', 
            'menu_item_material',
            'raw_material_usage',
            'material_purchase',
            'warehouse_transfer',
            'warehouse_material_min_stock',
            'pre_production_item_material',
            'pre_production_stock',
            'pre_production_production',
            'pre_production_transfer',
            'snap_settlement',
            'action_log',
            # Parent tables
            'order',
            'menu_item',
            'category',
            'customer',
            'pre_production_item',
            'warehouse',
            'raw_material',
            'cost_formula_settings',
            'table_area',
            'table',  # SQL keyword, needs special handling
        ]
        
        # Delete from all known tables
        for table_name in all_tables_to_clear:
            if table_name in table_names:
                try:
                    # Use quotes for SQL keywords like 'table'
                    if table_name == 'table':
                        s.execute(text('DELETE FROM "table"'))
                    else:
                        s.execute(text(f'DELETE FROM "{table_name}"'))
                except Exception as e:
                    print(f"Warning: Could not delete from {table_name}: {e}")
                    pass
        
        # Delete from ANY other tables that might exist (except settings and user)
        # This catches any tables we might have missed
        protected_tables = {'settings', 'user'}
        for table_name in table_names:
            if table_name not in all_tables_to_clear and table_name not in protected_tables:
                try:
                    s.execute(text(f'DELETE FROM "{table_name}"'))
                    print(f"Cleared additional table: {table_name}")
                except Exception as e:
                    print(f"Warning: Could not delete from {table_name}: {e}")
                    pass
        
        # Re-enable foreign key constraints
        s.execute(text("PRAGMA foreign_keys=ON"))
        s.commit()
    
    print(f"✅ Cleared all data from all tables in tenant database")

    # Update config.py in tenant to point to its own database
    config_py_path = os.path.join(root_dir, 'config.py')
    if os.path.exists(config_py_path):
        with open(config_py_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # Replace SQLALCHEMY_DATABASE_URI to point to tenant's DB
        import re
        # Pattern to match SQLALCHEMY_DATABASE_URI assignment (including multi-line with parentheses)
        # Match either: SQLALCHEMY_DATABASE_URI = (...) or SQLALCHEMY_DATABASE_URI = single_line_value
        pattern = r"SQLALCHEMY_DATABASE_URI\s*=\s*\([^)]*\)|SQLALCHEMY_DATABASE_URI\s*=\s*[^\n]+"
        # Normalize path to POSIX style to avoid Windows backslash issues in regex replacement
        db_path_posix = db_path.replace("\\", "/")
        replacement = f"SQLALCHEMY_DATABASE_URI = f\"sqlite:///{db_path_posix}\""
        # Use lambda to avoid backslash interpretation issues
        config_content = re.sub(pattern, lambda m: replacement, config_content, flags=re.MULTILINE)
        # Clean up any orphaned lines that might remain (like "or f\"sqlite:///...\"")
        config_content = re.sub(r'\s+or\s+f["\'].*?["\']\s*\)\s*', '', config_content)
        
        # Remove master DB bind (tenants don't need it)
        config_content = re.sub(r"SQLALCHEMY_BINDS\s*=\s*\{[^}]*'master'[^}]*\}", "", config_content)
        config_content = re.sub(r"MASTER_DB_URI\s*=\s*[^\n]+", "", config_content)
        
        with open(config_py_path, 'w', encoding='utf-8') as f:
            f.write(config_content)

    # Seed settings row so templates can show cafe name early
    # Also create default admin user
    Session = sessionmaker(bind=engine, future=True)
    iran_tz = pytz.timezone("Asia/Tehran")
    with Session() as s:
        existing_settings = s.query(Settings).first()
        if not existing_settings:
            s.add(Settings(cafe_name=name))
        
        # Create default admin user if none exists
        existing_user = s.query(User).first()
        if not existing_user:
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                name='مدیر سیستم',
                role='admin',
                is_active=True,
                created_at=datetime.now(iran_tz)
            )
            s.add(admin_user)
        
        s.commit()

    return ProvisionedTenant(
        name=name,
        slug=slug,
        root_dir=root_dir,
        db_path=db_path,
    )

