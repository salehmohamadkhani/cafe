from __future__ import annotations

import json
import os
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

from models.master_models import (
    CafeEventLog,
    CafeModule,
    CafeTenant,
    CafeWarehouseDefinition,
    CafeWarehouseProfile,
    MasterUser,
)
from models.models import InventoryConfiguration, Warehouse, db
from services.tenant_provisioning import normalize_slug, normalize_warehouse_plan, provision_tenant


MODULE_CATALOG = (
    ("orders", "فروش و صندوق"),
    ("inventory", "انبار و پیش‌تولید"),
    ("accounting", "حسابداری"),
    ("customers", "باشگاه مشتریان"),
    ("reports", "گزارش‌ها"),
    ("menu", "منو و قیمت‌گذاری"),
    ("users", "کاربران و نقش‌ها"),
)
MODULE_CODES = frozenset(code for code, _ in MODULE_CATALOG)


@dataclass(frozen=True)
class DemoCafe:
    name: str
    slug: str
    modules: tuple[str, ...]
    username: str
    password: str
    role: str
    user_name: str
    warehouse_mode: str = 'none'
    warehouse_names: tuple[str, ...] = ()


DEMO_CAFES = (
    DemoCafe(
        name="کافه مدلین",
        slug="madeline",
        modules=tuple(MODULE_CODES),
        username="admin",
        password="admin123",
        role="admin",
        user_name="مدیر کافه مدلین",
        warehouse_mode='multi',
        warehouse_names=('انبار مرکزی', 'انبار آشپزخانه', 'انبار بار و سرویس'),
    ),
    DemoCafe(
        name="کافه کیوسک",
        slug="kiosk",
        modules=("orders", "customers", "reports", "menu"),
        username="cashier",
        password="cashier123",
        role="cashier",
        user_name="صندوق‌دار کیوسک",
    ),
    DemoCafe(
        name="کافه روستری",
        slug="roastery",
        modules=("inventory", "menu", "reports", "users"),
        username="inventory",
        password="inventory123",
        role="inventory",
        user_name="مسئول انبار روستری",
        warehouse_mode='central',
        warehouse_names=('انبار مرکزی روستری',),
    ),
)


def ensure_master_admin(username: str = "admin", password: str = "admin") -> MasterUser:
    """Create the initial master user once; never reset an existing password."""
    username = (username or "admin").strip()
    password = password or "admin"
    if len(username) < 3 or len(password) < 5:
        raise ValueError("master credentials are too short")

    user = MasterUser.query.filter_by(username=username).first()
    if user:
        if not user.password_hash:
            user.password_hash = generate_password_hash(password)
            user.is_active = True
            db.session.commit()
        return user

    user = MasterUser(
        username=username,
        phone_number=f"local:{username}",
        password_hash=generate_password_hash(password),
        role="superadmin",
        is_active=True,
    )
    db.session.add(user)
    db.session.commit()
    return user


def enabled_module_codes(cafe_id: int) -> set[str]:
    rows = CafeModule.query.filter_by(cafe_id=cafe_id, is_enabled=True).all()
    return {row.module_code for row in rows}


def set_cafe_modules(cafe: CafeTenant, requested_codes: list[str] | tuple[str, ...] | set[str]) -> set[str]:
    selected = set(requested_codes) & MODULE_CODES
    existing = {row.module_code: row for row in CafeModule.query.filter_by(cafe_id=cafe.id).all()}
    for code in MODULE_CODES:
        row = existing.get(code)
        if row is None:
            db.session.add(CafeModule(cafe_id=cafe.id, module_code=code, is_enabled=code in selected))
        else:
            row.is_enabled = code in selected
    return selected


def log_cafe_event(cafe: CafeTenant, event_type: str, payload: dict | None = None) -> None:
    db.session.add(
        CafeEventLog(
            cafe_id=cafe.id,
            event_type=event_type,
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
        )
    )


def set_cafe_warehouse_profile(
    cafe: CafeTenant,
    mode: str,
    warehouses: tuple[tuple[str, str], ...],
) -> CafeWarehouseProfile:
    """Persist the canonical warehouse topology in the mother database."""
    profile = CafeWarehouseProfile.query.filter_by(cafe_id=cafe.id).first()
    if profile is None:
        profile = CafeWarehouseProfile(cafe_id=cafe.id)
        db.session.add(profile)
    profile.mode = mode
    profile.is_enabled = mode != 'none'

    CafeWarehouseDefinition.query.filter_by(cafe_id=cafe.id).delete(synchronize_session=False)
    for position, (code, name) in enumerate(warehouses):
        db.session.add(
            CafeWarehouseDefinition(
                cafe_id=cafe.id,
                code=code,
                name=name,
                position=position,
                is_active=True,
            )
        )
    return profile


def warehouse_profile_for_cafe(cafe_id: int) -> dict:
    profile = CafeWarehouseProfile.query.filter_by(cafe_id=cafe_id).first()
    rows = (
        CafeWarehouseDefinition.query.filter_by(cafe_id=cafe_id, is_active=True)
        .order_by(CafeWarehouseDefinition.position.asc())
        .all()
    )
    return {
        'mode': profile.mode if profile else 'none',
        'is_enabled': bool(profile and profile.is_enabled),
        'warehouses': rows,
    }


def ensure_cafe_warehouse_profile(cafe: CafeTenant) -> dict:
    """Backfill the new inventory contract for existing tenants without deleting data."""
    current = CafeWarehouseProfile.query.filter_by(cafe_id=cafe.id).first()
    if current:
        return warehouse_profile_for_cafe(cafe.id)

    inventory_enabled = 'inventory' in enabled_module_codes(cafe.id)
    mode = 'none'
    plan: tuple[tuple[str, str], ...] = ()
    if inventory_enabled and os.path.exists(cafe.db_path):
        engine = create_engine(f"sqlite:///{cafe.db_path}", future=True)
        try:
            db.metadata.create_all(bind=engine)
            Session = sessionmaker(bind=engine, future=True)
            with Session.begin() as tenant_session:
                rows = tenant_session.query(Warehouse).order_by(Warehouse.id.asc()).all()
                if not rows:
                    rows = [Warehouse(code='central', name='انبار مرکزی', is_active=True)]
                    tenant_session.add_all(rows)
                    tenant_session.flush()
                plan = tuple((row.code, row.name) for row in rows if row.is_active)
                mode = 'central' if len(plan) == 1 else 'multi'
                config = tenant_session.query(InventoryConfiguration).first()
                if config is None:
                    config = InventoryConfiguration()
                    tenant_session.add(config)
                config.is_enabled = True
                config.warehouse_mode = mode
                config.managed_by_master = True
        finally:
            engine.dispose()

    set_cafe_warehouse_profile(cafe, mode, plan)
    db.session.commit()
    return warehouse_profile_for_cafe(cafe.id)


def create_managed_cafe(
    *,
    tenants_dir: str,
    name: str,
    slug: str,
    modules: list[str] | tuple[str, ...] | set[str],
    username: str,
    password: str,
    role: str,
    user_name: str,
    warehouse_mode: str = 'none',
    warehouse_names: list[str] | tuple[str, ...] | None = None,
) -> CafeTenant:
    normalized_slug = normalize_slug(slug or name)
    if CafeTenant.query.filter_by(slug=normalized_slug).first():
        raise ValueError("این کد کافه قبلاً ثبت شده است.")

    selected_modules = set(modules) & MODULE_CODES
    normalized_mode, warehouse_plan = normalize_warehouse_plan(
        warehouse_mode,
        warehouse_names,
        inventory_enabled='inventory' in selected_modules,
    )
    provisioned = provision_tenant(
        tenants_dir=tenants_dir,
        name=name,
        slug=normalized_slug,
        admin_username=username,
        admin_password=password,
        admin_name=user_name,
        admin_role=role,
        warehouse_mode=normalized_mode,
        warehouses=warehouse_plan,
    )
    cafe = CafeTenant(
        name=provisioned.name,
        slug=provisioned.slug,
        root_dir=provisioned.root_dir,
        db_path=provisioned.db_path,
        is_active=True,
    )
    db.session.add(cafe)
    db.session.flush()
    selected = set_cafe_modules(cafe, selected_modules)
    set_cafe_warehouse_profile(cafe, normalized_mode, warehouse_plan)
    log_cafe_event(
        cafe,
        "cafe.created",
        {
            "modules": sorted(selected),
            "primary_username": username,
            "primary_role": role,
            "warehouse_mode": normalized_mode,
            "warehouses": [name for _, name in warehouse_plan],
        },
    )
    db.session.commit()
    return cafe


def seed_demo_cafes(tenants_dir: str) -> list[CafeTenant]:
    created: list[CafeTenant] = []
    for demo in DEMO_CAFES:
        existing = CafeTenant.query.filter_by(slug=demo.slug).first()
        if existing:
            continue
        created.append(
            create_managed_cafe(
                tenants_dir=tenants_dir,
                name=demo.name,
                slug=demo.slug,
                modules=demo.modules,
                username=demo.username,
                password=demo.password,
                role=demo.role,
                user_name=demo.user_name,
                warehouse_mode=demo.warehouse_mode,
                warehouse_names=demo.warehouse_names,
            )
        )
    return created


def module_for_endpoint(endpoint: str | None) -> str | None:
    """Map a tenant request endpoint to the centrally controlled module."""
    endpoint = endpoint or ""
    if endpoint.startswith(("order.", "table.", "takeaway.", "pos.")):
        return "orders"
    if endpoint.startswith("menu."):
        return "menu"
    if endpoint in {"admin.inventory_dashboard", "admin.warehouses_management"}:
        return "inventory"
    if endpoint.startswith("admin.create_warehouse") or endpoint.startswith("admin.check_warehouse"):
        return "inventory"
    if endpoint.startswith("admin.create_raw_material") or endpoint.startswith("admin.update_raw_material"):
        return "inventory"
    if endpoint.startswith("admin.delete_raw_material") or endpoint.startswith("admin.create_material_purchase"):
        return "inventory"
    if endpoint.startswith("admin.update_material_purchase") or endpoint.startswith("admin.delete_material_purchase"):
        return "inventory"
    if "pre_production" in endpoint or endpoint == "admin.clear_all_inventory_data":
        return "inventory"
    if endpoint in {"admin.financial_report", "admin.settle_snap"}:
        return "accounting"
    if endpoint == "admin.customers_leaderboard":
        return "customers"
    if endpoint in {
        "admin.users_list",
        "admin.request_user_creation",
        "admin.add_user",
        "admin.edit_user",
        "admin.delete_user",
    }:
        return "users"
    if endpoint in {"admin.orders_report", "admin.search_orders", "admin.invoice"}:
        return "reports"
    return None
