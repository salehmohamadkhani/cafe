from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime

import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

from models.models import InventoryConfiguration, Settings, User, Warehouse, db


_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TENANT_ROLES = {
    "admin",
    "cashier",
    "inventory",
    "procurement",
    "accountant",
    "waiter",
}
WAREHOUSE_MODES = frozenset({'none', 'central', 'multi'})


def normalize_warehouse_plan(
    mode: str,
    warehouse_names: list[str] | tuple[str, ...] | None = None,
    *,
    inventory_enabled: bool = True,
) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Validate and normalize a cafe's initial warehouse topology."""
    if not inventory_enabled:
        return 'none', ()

    mode = (mode or 'central').strip().lower()
    if mode not in WAREHOUSE_MODES:
        raise ValueError('warehouse mode is invalid')
    if mode == 'none':
        return 'none', ()

    cleaned: list[str] = []
    for value in warehouse_names or ():
        name = (value or '').strip()
        if name and name not in cleaned:
            cleaned.append(name)

    if mode == 'central':
        name = cleaned[0] if cleaned else 'انبار مرکزی'
        return mode, (('central', name),)

    if len(cleaned) < 2:
        raise ValueError('برای حالت چندانباره، حداقل دو انبار تعریف کنید.')
    if len(cleaned) > 12:
        raise ValueError('حداکثر ۱۲ انبار برای هر کافه قابل تعریف است.')
    return mode, tuple(
        ('central' if index == 0 else f'warehouse-{index + 1}', name)
        for index, name in enumerate(cleaned)
    )


def normalize_slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def validate_slug(slug: str) -> bool:
    return bool(slug and _SLUG_RE.fullmatch(slug))


@dataclass(frozen=True)
class ProvisionedTenant:
    name: str
    slug: str
    root_dir: str
    db_path: str
    admin_username: str
    admin_role: str


def provision_tenant(
    tenants_dir: str,
    name: str,
    slug: str,
    source_project_dir: str | None = None,
    admin_username: str = "admin",
    admin_password: str = "admin123",
    admin_name: str = "مدیر کافه",
    admin_role: str = "admin",
    warehouse_mode: str = 'none',
    warehouses: tuple[tuple[str, str], ...] = (),
) -> ProvisionedTenant:
    """Create one isolated tenant database under the shared application.

    ``source_project_dir`` remains in the signature for compatibility with older
    callers, but source code is deliberately not copied. All cafes run the same
    codebase; only their runtime data is isolated.
    """
    del source_project_dir

    raw_tenants_dir = (tenants_dir or "").strip()
    if not raw_tenants_dir:
        raise ValueError("tenants_dir is required")
    tenants_dir = os.path.abspath(raw_tenants_dir)

    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")

    slug = normalize_slug(slug or name)
    if not validate_slug(slug):
        raise ValueError("slug is invalid (use a-z, 0-9, dash)")

    admin_username = (admin_username or "").strip()
    admin_password = admin_password or ""
    admin_name = (admin_name or "").strip() or "مدیر کافه"
    admin_role = (admin_role or "admin").strip().lower()
    if len(admin_username) < 3:
        raise ValueError("admin username must contain at least 3 characters")
    if len(admin_password) < 6:
        raise ValueError("admin password must contain at least 6 characters")
    if admin_role not in _TENANT_ROLES:
        raise ValueError("admin role is invalid")

    root_dir = os.path.abspath(os.path.join(tenants_dir, slug))
    common_root = os.path.commonpath([tenants_dir, root_dir])
    if common_root != tenants_dir:
        raise ValueError("tenant path is outside tenants_dir")
    if os.path.exists(root_dir):
        raise ValueError(f"tenant directory already exists: {root_dir}")

    instance_dir = os.path.join(root_dir, "instance")
    os.makedirs(instance_dir, exist_ok=False)
    db_path = os.path.join(instance_dir, "cafe.db")
    engine = create_engine(f"sqlite:///{db_path}", future=True)

    try:
        db.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, future=True)
        iran_tz = pytz.timezone("Asia/Tehran")
        with Session.begin() as tenant_session:
            tenant_session.add(Settings(cafe_name=name))
            tenant_session.add(
                InventoryConfiguration(
                    is_enabled=warehouse_mode != 'none',
                    warehouse_mode=warehouse_mode,
                    managed_by_master=True,
                )
            )
            for code, warehouse_name in warehouses:
                tenant_session.add(Warehouse(code=code, name=warehouse_name, is_active=True))
            tenant_session.add(
                User(
                    username=admin_username,
                    password_hash=generate_password_hash(admin_password),
                    name=admin_name,
                    role=admin_role,
                    is_active=True,
                    created_at=datetime.now(iran_tz),
                )
            )
    finally:
        engine.dispose()

    return ProvisionedTenant(
        name=name,
        slug=slug,
        root_dir=root_dir,
        db_path=db_path,
        admin_username=admin_username,
        admin_role=admin_role,
    )
