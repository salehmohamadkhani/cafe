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
                if item.startswith('.'):
                    continue
                src_path = os.path.join(src, item)
                dst_path = os.path.join(dst, item)
                
                if should_exclude(src_path):
                    continue
                
                if os.path.isdir(src_path):
                    if item not in ['tenants', '.git', 'venv', '.venv']:
                        copy_tree(src_path, dst_path)
                else:
                    if not should_exclude(src_path):
                        shutil.copy2(src_path, dst_path)
        
        copy_tree(source_project_dir, root_dir)
        
        # Clean up instance directory (we'll create fresh DB)
        instance_dir = os.path.join(root_dir, 'instance')
        if os.path.exists(instance_dir):
            for item in os.listdir(instance_dir):
                item_path = os.path.join(instance_dir, item)
                if item.endswith('.db') or item == 'secret_key':
                    try:
                        os.remove(item_path)
                    except:
                        pass
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

