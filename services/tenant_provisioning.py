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


def provision_tenant(tenants_dir: str, name: str, slug: str) -> ProvisionedTenant:
    """
    Creates folder structure + a fresh sqlite db for a new cafe tenant.
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

