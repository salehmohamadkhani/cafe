from collections import defaultdict
from datetime import date
import math

from models.models import (
    db,
    MenuItem,
    MaterialPurchase,
    RawMaterial,
    RawMaterialUsage,
    convert_unit,
)
from sqlalchemy import cast, Date


def purchase_base_quantity(purchase: MaterialPurchase) -> float:
    material = purchase.raw_material
    if not material:
        return float(purchase.quantity or 0)
    return convert_unit(purchase.quantity, purchase.unit, material.default_unit)


def weighted_average_unit_price(material: RawMaterial) -> float | None:
    """Return weighted average purchase cost in the material base unit."""
    total_quantity = 0.0
    total_value = 0.0
    for purchase in material.purchases:
        quantity = purchase_base_quantity(purchase)
        if quantity <= 0:
            continue
        total_quantity += quantity
        total_value += float(purchase.total_price or 0)
    return (total_value / total_quantity) if total_quantity > 0 else None


def menu_item_available_quantity(item: MenuItem) -> int:
    """Return the sellable quantity from the recipe, or the legacy item stock.

    Recipe-backed products are constrained by their least-available ingredient.
    This keeps the order screen aligned with the inventory ledger instead of the
    old, unrelated ``menu_item.stock`` counter.
    """
    requirements: dict[int, tuple[RawMaterial, float]] = {}
    for part in item.materials:
        quantity = part.quantity_value
        if not quantity or quantity <= 0:
            continue
        if part.raw_material:
            required_base = convert_unit(quantity, part.unit, part.raw_material.default_unit)
            previous = requirements.get(part.raw_material.id, (part.raw_material, 0.0))[1]
            requirements[part.raw_material.id] = (part.raw_material, previous + required_base)
        elif part.pre_production_item:
            pre_item = part.pre_production_item
            multiplier = convert_unit(quantity, part.unit, pre_item.unit)
            for component in pre_item.materials:
                if not component.raw_material:
                    continue
                required_base = convert_unit(
                    float(component.quantity or 0) * multiplier,
                    component.unit,
                    component.raw_material.default_unit,
                )
                previous = requirements.get(component.raw_material.id, (component.raw_material, 0.0))[1]
                requirements[component.raw_material.id] = (component.raw_material, previous + required_base)

    capacities: list[int] = []
    for raw_material, required_base in requirements.values():
        if required_base <= 0:
            continue
        capacities.append(math.floor(float(raw_material.current_stock or 0) / required_base))

    if capacities:
        return max(0, min(capacities))
    return max(0, int(item.stock or 0))


def menu_stock_map(items: list[MenuItem] | None = None) -> dict[int, int]:
    items = items if items is not None else MenuItem.query.filter_by(is_active=True).all()
    return {item.id: menu_item_available_quantity(item) for item in items}


def calculate_material_stock_for_period(
    raw_materials,
    purchases,
    start_date: date | None,
    end_date: date | None,
) -> dict[int, float]:
    """
    بر اساس خریدها و مصرف سفارش‌ها، موجودی پایان بازه را برای هر ماده اولیه حساب می‌کند.
    خروجی: دیکشنری {raw_material_id: stock}
    """
    # ۱) موجودی اولیه را از فیلد فعلی مدل (مثلاً current_stock) بگیر
    # اما برای محاسبه دقیق‌تر، باید خریدها و مصرف‌های قبل از start_date را هم حساب کنیم
    opening = {}
    for m in raw_materials:
        if start_date:
            # اگر start_date مشخص است، موجودی ابتدای دوره را محاسبه می‌کنیم
            # تمام خریدها تا قبل از start_date
            purchases_before = MaterialPurchase.query.filter(
                MaterialPurchase.raw_material_id == m.id,
                MaterialPurchase.purchase_date < start_date
            ).all()
            
            # تمام مصرف‌ها تا قبل از start_date
            usages_before = RawMaterialUsage.query.filter(
                RawMaterialUsage.raw_material_id == m.id,
                cast(RawMaterialUsage.created_at, Date) < start_date
            ).all()
            
            # محاسبه موجودی ابتدای دوره
            base_unit = m.default_unit
            stock_before = 0.0
            for p in purchases_before:
                stock_before += convert_unit(p.quantity, p.unit, base_unit)
            for u in usages_before:
                stock_before -= convert_unit(u.quantity, u.unit, base_unit)
            
            opening[m.id] = max(0.0, stock_before)
        else:
            # اگر start_date مشخص نیست، موجودی را از تمام خریدها و مصرف‌ها محاسبه می‌کنیم
            # (نه از current_stock که ممکن است به‌روز نباشد)
            purchases_all = MaterialPurchase.query.filter(
                MaterialPurchase.raw_material_id == m.id
            ).all()
            
            usages_all = RawMaterialUsage.query.filter(
                RawMaterialUsage.raw_material_id == m.id
            ).all()
            
            base_unit = m.default_unit
            stock_calculated = 0.0
            for p in purchases_all:
                stock_calculated += convert_unit(p.quantity, p.unit, base_unit)
            for u in usages_all:
                stock_calculated -= convert_unit(u.quantity, u.unit, base_unit)
            
            opening[m.id] = max(0.0, stock_calculated)

    # ۲) تغییرات موجودی در بازه را بر اساس خریدها حساب کن
    # فقط اگر start_date مشخص باشد، باید تغییرات را محاسبه کنیم
    # در غیر این صورت، opening قبلاً شامل تمام خریدهاست
    delta = defaultdict(float)
    
    if start_date:
        # فقط اگر start_date مشخص باشد، تغییرات در بازه را محاسبه می‌کنیم
        for p in purchases:
            rm_id = p.raw_material_id
            if not rm_id:
                continue
            raw_material = next((m for m in raw_materials if m.id == rm_id), None)
            if not raw_material:
                continue
            
            qty = float(getattr(p, "quantity", 0) or 0)
            base_unit = raw_material.default_unit
            converted_qty = convert_unit(qty, p.unit, base_unit)
            delta[rm_id] += converted_qty

        # ۳) مصرف در سفارش‌ها/رسپی‌ها را هم در همین بازه کم کن
        usages_query = RawMaterialUsage.query
        
        usages_query = usages_query.filter(
            cast(RawMaterialUsage.created_at, Date) >= start_date
        )
        if end_date:
            usages_query = usages_query.filter(
                cast(RawMaterialUsage.created_at, Date) <= end_date
            )
        
        usages_in_period = usages_query.all()
        
        for usage in usages_in_period:
            rm_id = usage.raw_material_id
            if not rm_id:
                continue
            raw_material = next((m for m in raw_materials if m.id == rm_id), None)
            if not raw_material:
                continue
            
            qty = float(getattr(usage, "quantity", 0) or 0)
            base_unit = raw_material.default_unit
            converted_qty = convert_unit(qty, usage.unit, base_unit)
            delta[rm_id] -= converted_qty

    # محاسبه نتیجه نهایی
    result = {}
    for m in raw_materials:
        base = opening.get(m.id, 0.0)
        change = delta.get(m.id, 0.0)
        result[m.id] = max(0.0, base + change)

    return result

