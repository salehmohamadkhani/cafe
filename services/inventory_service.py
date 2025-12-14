from collections import defaultdict
from datetime import date
from models.models import db, RawMaterial, MaterialPurchase, RawMaterialUsage, convert_unit
from sqlalchemy import cast, Date


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
            # اگر start_date مشخص نیست، از current_stock استفاده می‌کنیم
            opening[m.id] = float(getattr(m, "current_stock", 0) or 0)

    # ۲) تغییرات موجودی در بازه را بر اساس خریدها حساب کن
    delta = defaultdict(float)
    
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
    
    if start_date:
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

