from sqlalchemy.exc import IntegrityError

from data.inventory_seed import RAW_MATERIAL_PURCHASES
from utils.helpers import parse_jalali_date
from models.models import RawMaterial, MaterialPurchase, db


def _clean_number(value):
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return value
    value = str(value).strip()
    if not value:
        return 0
    value = value.replace(',', '').replace('٬', '').replace(' ', '')
    try:
        return float(value)
    except ValueError:
        return 0


def seed_inventory_if_needed():
    if RawMaterial.query.count() > 0:
        return

    for entry in RAW_MATERIAL_PURCHASES:
        name = (entry.get('name') or '').strip()
        if not name:
            continue

        unit = (entry.get('unit') or 'gr').strip()
        raw_material = RawMaterial.query.filter_by(name=name).first()
        if not raw_material:
            code = entry.get('code')
            raw_material = RawMaterial(name=name, code=code, default_unit=unit)
            db.session.add(raw_material)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                raw_material = RawMaterial.query.filter_by(name=name).first()
                if not raw_material:
                    continue

        quantity = _clean_number(entry.get('quantity'))
        total_price = _clean_number(entry.get('total_price'))
        purchase_date = parse_jalali_date(entry.get('date'))

        purchase = MaterialPurchase(
            raw_material_id=raw_material.id,
            purchase_date=purchase_date,
            quantity=quantity,
            unit=unit,
            total_price=int(total_price),
            vendor_name=(entry.get('vendor_name') or '').strip() or None,
            vendor_phone=(entry.get('vendor_phone') or '').strip() or None,
            note=entry.get('note')
        )
        db.session.add(purchase)

    db.session.commit()
