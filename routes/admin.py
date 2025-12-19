from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask import current_app as app
from flask_login import login_required, current_user
from models.models import db, Settings, Order, OrderItem, Customer, User, RawMaterial, MaterialPurchase, Table, TableArea, TableItem, SnapSettlement, Warehouse, WarehouseTransfer, RawMaterialUsage, MenuItemMaterial, calculate_order_amount, convert_unit
from utils.helpers import to_jalali, categorize_payment_method, PAYMENT_BUCKET_LABELS
from sqlalchemy import func, extract, or_, text
from services.inventory_service import calculate_material_stock_for_period
from collections import defaultdict
from datetime import datetime, timedelta, date
import pytz
from utils.seed_inventory import seed_inventory_if_needed
from werkzeug.security import generate_password_hash


DEFAULT_WAREHOUSES = [
    ("central", "انبار مرکزی"),
    ("kitchen_western", "انبار آشپزخانه فرنگی"),
    ("kitchen_iranian", "انبار آشپزخانه ایرانی"),
    ("hookah", "انبار قلیان"),
    ("bar", "انبار بار"),
]


def seed_warehouses_if_needed():
    """Create default warehouses if they do not exist."""
    created_any = False
    for code, name in DEFAULT_WAREHOUSES:
        existing = Warehouse.query.filter_by(code=code).first()
        if existing:
            continue
        wh = Warehouse(code=code, name=name, is_active=True)
        db.session.add(wh)
        created_any = True
    if created_any:
        db.session.commit()


def get_central_warehouse() -> Warehouse | None:
    return Warehouse.query.filter_by(code='central').first()


def warehouse_transfer_sums(warehouse_id: int, direction: str, end_date: date | None = None) -> dict[int, float]:
    """
    direction: 'in' or 'out'
    returns {raw_material_id: sum(base_quantity)}
    """
    q = db.session.query(
        WarehouseTransfer.raw_material_id.label('rm_id'),
        func.coalesce(func.sum(WarehouseTransfer.base_quantity), 0).label('qty')
    )
    if direction == 'in':
        q = q.filter(WarehouseTransfer.to_warehouse_id == warehouse_id)
    else:
        q = q.filter(WarehouseTransfer.from_warehouse_id == warehouse_id)
    if end_date:
        q = q.filter(WarehouseTransfer.transfer_date <= end_date)
    q = q.group_by(WarehouseTransfer.raw_material_id)
    rows = q.all()
    return {int(r.rm_id): float(r.qty or 0) for r in rows if r and r.rm_id is not None}


def compute_warehouse_stock_for_material(raw_material: RawMaterial, warehouse: Warehouse, end_date: date | None = None) -> float:
    """Compute warehouse stock in base unit (raw_material.default_unit)."""
    incoming = warehouse_transfer_sums(warehouse.id, 'in', end_date=end_date).get(raw_material.id, 0.0)
    outgoing = warehouse_transfer_sums(warehouse.id, 'out', end_date=end_date).get(raw_material.id, 0.0)
    base = 0.0
    if warehouse.code == 'central':
        # Central base stock comes from purchases/usages (current_stock), transfers adjust it.
        base = float(raw_material.current_stock or 0)
    return max(0.0, base + incoming - outgoing)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

USER_ROLE_DEFINITIONS = {
    'admin': {
        'label': 'مدیر',
        'description': 'دسترسی کامل به همه ماژول‌ها و تنظیمات سیستم',
        'permissions': ['مدیریت کاربران', 'گزارش‌های مالی', 'تنظیمات کلی']
    },
    'cashier': {
        'label': 'صندوق‌دار',
        'description': 'مدیریت سفارش‌ها و ثبت پرداخت‌ها در سالن و بیرون‌بر',
        'permissions': ['داشبورد سفارش', 'پرداخت‌ها', 'گزارش فروش روزانه']
    },
    'inventory': {
        'label': 'انباردار',
        'description': 'مدیریت موجودی، مواد اولیه و گزارش‌های انبار',
        'permissions': ['داشبورد انبار', 'ثبت ورود/خروج مواد', 'هشدار موجودی']
    },
    'procurement': {
        'label': 'مسئول خرید',
        'description': 'ثبت خرید مواد و پیگیری تامین‌کنندگان',
        'permissions': ['ثبت خرید', 'مدیریت تامین‌کننده', 'گزارش هزینه خرید']
    },
    'accountant': {
        'label': 'حسابدار',
        'description': 'مشاهده گزارش‌های مالی و صدور اسناد حسابرسی',
        'permissions': ['گزارش مالی', 'فاکتورهای روزانه', 'مالیات و تخفیف‌ها']
    },
    'waiter': {
        'label': 'گارسون',
        'description': 'ثبت سفارش حضوری و پیگیری میزهای خود',
        'permissions': ['مدیریت میز', 'ثبت سفارش', 'وضعیت پرداخت مشتری']
    }
}

# --- صفحه راهنمای طراحی / UI Kit ---
@admin_bp.route('/ui-kit')
@login_required
def ui_kit():
    # This page is intentionally disabled (hidden from menu + not accessible).
    abort(404)
    light_palette = [
        {'role': 'Primary', 'name': 'Royal Navy', 'hex': '#1F3A5F'},
        {'role': 'Primary Light', 'name': 'Royal Navy 20%', 'hex': '#3A5078'},
        {'role': 'Secondary', 'name': 'Sky Blue', 'hex': '#4AA8FF'},
        {'role': 'Accent 1', 'name': 'Coffee Brown', 'hex': '#6A4E36'},
        {'role': 'Accent 2', 'name': 'Cream Beige', 'hex': '#F1E7D0'},
        {'role': 'Success', 'name': 'Cafe Green', 'hex': '#27B376'},
        {'role': 'Warning', 'name': 'Warm Amber', 'hex': '#F2B544'},
        {'role': 'Danger', 'name': 'Soft Red', 'hex': '#E44848'},
        {'role': 'Background', 'name': 'Main Background', 'hex': '#F7F8FA'},
        {'role': 'Surface', 'name': 'Cards / Topbars', 'hex': '#FFFFFF'},
        {'role': 'Border', 'name': 'Dividers', 'hex': '#D8DDE3'},
        {'role': 'Text Primary', 'name': 'Dark Gray', 'hex': '#2A2E34'},
        {'role': 'Text Secondary', 'name': 'Medium Gray', 'hex': '#6B7380'},
        {'role': 'Disabled', 'name': 'Gray Muted', 'hex': '#C8CDD4'},
    ]

    dark_palette = [
        {'role': 'Primary', 'name': 'Royal Navy (Brightened)', 'hex': '#2D4F82'},
        {'role': 'Primary Dark', 'name': 'Navy Deep', 'hex': '#152233'},
        {'role': 'Secondary', 'name': 'Sky Blue (Softened)', 'hex': '#61B5FF'},
        {'role': 'Accent 1', 'name': 'Coffee Brown Dark', 'hex': '#4F3A28'},
        {'role': 'Accent 2', 'name': 'Cream Soft', 'hex': '#E6D9BC'},
        {'role': 'Success', 'name': 'Cafe Green Dark', 'hex': '#2ECF8F'},
        {'role': 'Warning', 'name': 'Amber Dark', 'hex': '#F4C25C'},
        {'role': 'Danger', 'name': 'Red Bright', 'hex': '#FF6666'},
        {'role': 'Background', 'name': 'Main Dark BG', 'hex': '#111418'},
        {'role': 'Surface', 'name': 'Cards / Panels', 'hex': '#1A1E23'},
        {'role': 'Border', 'name': 'Soft Gray', 'hex': '#2A3038'},
        {'role': 'Text Primary', 'name': 'White', 'hex': '#F5F6F7'},
        {'role': 'Text Secondary', 'name': 'Gray 60%', 'hex': '#B3B9C2'},
        {'role': 'Disabled', 'name': 'Muted Gray', 'hex': '#3F454F'},
    ]
    return render_template('admin/ui_kit.html', light_palette=light_palette, dark_palette=dark_palette)

# --- داشبورد مدیریتی ---
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    seed_inventory_if_needed()
    today = datetime.now().date()
    orders_today = Order.query.filter(func.date(Order.created_at) == today).all()
    total_orders = len(orders_today)
    total_sales = sum(o.final_amount for o in orders_today)
    unpaid_orders = [o for o in orders_today if o.status == 'پرداخت نشده']
    paid_orders = [o for o in orders_today if o.status == 'پرداخت شده']
    takeaway_orders = [o for o in orders_today if o.type == 'بیرون‌بر']

    # کارت‌های خلاصه
    summary = {
        'total_orders': total_orders,
        'total_sales': total_sales,
        'unpaid_orders': len(unpaid_orders),
        'paid_orders': len(paid_orders),
        'takeaway_orders': len(takeaway_orders),
    }
    # آخرین سفارش‌ها برای نمایش کارت‌ها
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(20).all()
    return render_template('dashboard.html', summary=summary, orders=recent_orders)

# --- تنظیمات سیستم ---
@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings = Settings.query.first()
    if not settings:
        settings = Settings(updated_at=datetime.utcnow())
        db.session.add(settings)
        db.session.commit()

    table_areas = TableArea.query.order_by(TableArea.name.asc()).all()
    tables = Table.query.order_by(Table.area_id.asc().nullsfirst(), Table.number.asc()).all()
    staff_count = User.query.count()

    if request.method == 'POST':
        form_type = request.form.get('form_type', 'business')
        try:
            if form_type == 'business':
                settings.cafe_name = request.form.get('business_name')
                settings.phone = request.form.get('phone')
                settings.address = request.form.get('address')
                settings.updated_at = datetime.utcnow()
                db.session.commit()
                flash('اطلاعات کسب‌وکار به‌روزرسانی شد.', 'success')
            elif form_type == 'financial':
                settings.tax_percent = float(request.form.get('tax_rate', settings.tax_percent or 9))
                settings.service_charge = float(request.form.get('service_charge', settings.service_charge or 0))
                card_number = (request.form.get('card_number') or '').strip()
                settings.card_number = card_number or None
                settings.updated_at = datetime.utcnow()
                db.session.commit()
                flash('تنظیمات مالی ذخیره شد.', 'success')
            elif form_type == 'social':
                settings.instagram = request.form.get('instagram')
                settings.telegram = request.form.get('telegram')
                settings.website = request.form.get('website')
                settings.updated_at = datetime.utcnow()
                db.session.commit()
                flash('لینک‌های شبکه‌های اجتماعی به‌روز شد.', 'success')
            elif form_type == 'table_area':
                name = (request.form.get('area_name') or '').strip()
                description = (request.form.get('area_description') or '').strip() or None
                if not name:
                    flash('نام دسته‌بندی میز الزامی است.', 'warning')
                elif TableArea.query.filter(func.lower(TableArea.name) == name.lower()).first():
                    flash('این نام قبلاً ثبت شده است.', 'warning')
                else:
                    area = TableArea(name=name, description=description)
                    db.session.add(area)
                    db.session.commit()
                    flash('دسته‌بندی جدید اضافه شد.', 'success')
            elif form_type == 'update_area':
                area_id = request.form.get('area_id')
                area = TableArea.query.get(area_id)
                if not area:
                    flash('دسته‌بندی موردنظر یافت نشد.', 'warning')
                else:
                    new_name = (request.form.get('area_name_update') or area.name).strip()
                    new_desc = (request.form.get('area_description_update') or '').strip() or None
                    if not new_name:
                        flash('نام جدید نمی‌تواند خالی باشد.', 'warning')
                    elif TableArea.query.filter(func.lower(TableArea.name) == new_name.lower(), TableArea.id != area.id).first():
                        flash('دسته‌ای با این نام وجود دارد.', 'warning')
                    else:
                        area.name = new_name
                        area.description = new_desc
                        db.session.commit()
                        flash('دسته‌بندی به‌روزرسانی شد.', 'success')
            elif form_type == 'delete_area':
                area_id = request.form.get('area_id')
                area = TableArea.query.get(area_id)
                if not area:
                    flash('دسته‌بندی یافت نشد.', 'warning')
                else:
                    Table.query.filter_by(area_id=area.id).update({'area_id': None})
                    db.session.delete(area)
                    db.session.commit()
                    flash('دسته‌بندی حذف شد و میزهای آن آزاد شدند.', 'success')
            elif form_type == 'add_table':
                area_id = request.form.get('area_id')
                area = None
                if area_id:
                    area = TableArea.query.get(area_id)
                    if not area:
                        flash('دسته‌بندی انتخاب‌شده یافت نشد.', 'warning')
                        return redirect(url_for('admin.settings'))
                table_count = max(1, int(request.form.get('table_count', 1)))
                start_number_raw = request.form.get('start_number')
                if start_number_raw:
                    base_number = int(start_number_raw)
                else:
                    max_number = db.session.query(func.coalesce(func.max(Table.number), 0)).scalar() or 0
                    base_number = max_number + 1
                existing_numbers = {num for (num,) in db.session.query(Table.number).all()}
                created = 0
                candidate = base_number
                while created < table_count:
                    while candidate in existing_numbers:
                        candidate += 1
                    table = Table(number=candidate, status='خالی', area_id=area.id if area else None)
                    db.session.add(table)
                    existing_numbers.add(candidate)
                    created += 1
                    candidate += 1
                db.session.commit()
                flash(f'{created} میز جدید به سیستم اضافه شد.', 'success')
            elif form_type == 'update_table':
                table_id = request.form.get('table_id')
                table = Table.query.get(table_id)
                if not table:
                    flash('میز انتخاب‌شده یافت نشد.', 'warning')
                else:
                    new_number_raw = request.form.get('new_number')
                    if new_number_raw:
                        try:
                            new_number = int(new_number_raw)
                        except ValueError:
                            flash('شماره میز باید عدد باشد.', 'warning')
                            return redirect(url_for('admin.settings'))
                        if new_number != table.number and Table.query.filter_by(number=new_number).first():
                            flash('شماره میز تکراری است.', 'warning')
                            return redirect(url_for('admin.settings'))
                        table.number = new_number
                    target_area_id = request.form.get('target_area_id')
                    if target_area_id:
                        area = TableArea.query.get(target_area_id)
                        if not area:
                            flash('دسته‌بندی انتخاب‌شده یافت نشد.', 'warning')
                            return redirect(url_for('admin.settings'))
                        table.area_id = area.id
                    else:
                        table.area_id = None
                    db.session.commit()
                    flash('اطلاعات میز به‌روز شد.', 'success')
            elif form_type == 'delete_table':
                table_id = request.form.get('table_id')
                table = Table.query.get(table_id)
                if not table:
                    flash('میز انتخاب‌شده یافت نشد.', 'warning')
                elif table.order_id:
                    flash('این میز در حال حاضر سفارش فعال دارد و قابل حذف نیست.', 'danger')
                else:
                    TableItem.query.filter_by(table_id=table.id).delete()
                    db.session.delete(table)
                    db.session.commit()
                    flash('میز حذف شد.', 'success')
            else:
                flash('نوع فرم ناشناخته است.', 'warning')
        except Exception as exc:
            db.session.rollback()
            flash(f'خطا در ذخیره تنظیمات: {exc}', 'danger')
        return redirect(url_for('admin.settings'))

    area_summaries = []
    for area in table_areas:
        numbers = [table.number for table in tables if table.area_id == area.id]
        area_summaries.append({'area': area, 'numbers': numbers})
    unassigned_tables = [table.number for table in tables if table.area_id is None]

    return render_template(
        'admin/settings.html',
        settings=settings,
        staff_count=staff_count,
        table_areas=table_areas,
        area_summaries=area_summaries,
        unassigned_tables=unassigned_tables,
        tables=tables
    )

# --- گزارش سفارش‌ها با جستجو و فیلتر ---
@admin_bp.route('/orders')
@login_required
def orders_report():
    # فیلتر بر اساس تاریخ، وضعیت، شماره فاکتور یا نام مشتری
    status = request.args.get('status')
    q = request.args.get('q')
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    orders_query = Order.query

    if status:
        orders_query = orders_query.filter_by(status=status)
    if q:
        try:
            q_int = int(q)
        except (TypeError, ValueError):
            q_int = None
        filters = [
            (Order.invoice_number == q),
            (Order.invoice_uid == q),
            (Customer.name.ilike(f'%{q}%')),
            (Customer.phone.ilike(f'%{q}%'))
        ]
        if q_int is not None:
            filters.append(Order.daily_sequence == q_int)
        orders_query = orders_query.join(Customer).filter(or_(*filters))
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            orders_query = orders_query.filter(Order.created_at >= date_from_dt)
        except:
            pass
    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            orders_query = orders_query.filter(Order.created_at <= date_to_dt)
        except:
            pass

    orders = orders_query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders_report.html', orders=orders)


@admin_bp.route('/customers/leaderboard')
@login_required
def customers_leaderboard():
    stats_query = (
        db.session.query(
            Customer.id.label('customer_id'),
            Customer.name.label('name'),
            Customer.phone.label('phone'),
            Customer.birth_date.label('birth_date'),
            func.count(Order.id).label('order_count'),
            func.sum(Order.final_amount).label('total_amount'),
            func.max(Order.created_at).label('last_order_at')
        )
        .join(Order, Order.customer_id == Customer.id)
        .group_by(Customer.id, Customer.birth_date)
        .having(func.count(Order.id) > 0)
    )

    stats = []
    for row in stats_query:
        last_order_jalali = to_jalali(row.last_order_at) if row.last_order_at else None
        birth_date_jalali = None
        if row.birth_date:
            # تبدیل تاریخ میلادی به شمسی
            try:
                birth_date_jalali = to_jalali(datetime.combine(row.birth_date, datetime.min.time()))
            except:
                birth_date_jalali = None
        stats.append({
            'id': row.customer_id,
            'name': row.name or 'مشتری ناشناس',
            'phone': row.phone or '-',
            'birth_date': row.birth_date.isoformat() if row.birth_date else None,
            'birth_date_jalali': birth_date_jalali,
            'order_count': int(row.order_count or 0),
            'total_amount': int(row.total_amount or 0),
            'last_order_at_iso': row.last_order_at.isoformat() if row.last_order_at else None,
            'last_order_jalali': last_order_jalali
        })

    top_by_orders = sorted(stats, key=lambda x: x['order_count'], reverse=True)[:20]
    top_by_amount = sorted(stats, key=lambda x: x['total_amount'], reverse=True)[:20]

    totals = {
        'customers': len(stats),
        'orders': sum(item['order_count'] for item in stats),
        'revenue': sum(item['total_amount'] for item in stats)
    }

    return render_template(
        'admin/customers_report.html',
        top_by_orders=top_by_orders,
        top_by_amount=top_by_amount,
        totals=totals
    )


# لیست واحدهای استاندارد برای مواد اولیه
RAW_MATERIAL_UNITS = ['gr', 'kg', 'ml', 'l', 'عدد', 'تیکه', 'بسته', 'متر', 'کیلو']

@admin_bp.route('/inventory')
@login_required
def inventory_dashboard():
    # فقط اگر داده‌ای وجود ندارد seed کن (نه همیشه)
    # seed_inventory_if_needed()  # غیرفعال شده تا بعد از حذف دوباره نسازد
    seed_warehouses_if_needed()
    central_wh = get_central_warehouse()

    # خواندن پارامترهای تاریخ و سرچ
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    search_query = request.args.get("q", "").strip()

    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    # اگر فقط start_date وارد شده و end_date نه، end_date را امروز بگیر
    if start_date and not end_date:
        end_date = date.today()

    raw_material_records = RawMaterial.query.order_by(RawMaterial.name.asc()).all()
    
    # فیلتر کردن خریدها بر اساس بازه زمانی
    purchases_query = MaterialPurchase.query.order_by(
        MaterialPurchase.purchase_date.desc(),
        MaterialPurchase.created_at.desc()
    )

    if start_date:
        purchases_query = purchases_query.filter(MaterialPurchase.purchase_date >= start_date)
    if end_date:
        purchases_query = purchases_query.filter(MaterialPurchase.purchase_date <= end_date)

    if search_query:
        like = f"%{search_query}%"
        purchases_query = purchases_query.join(RawMaterial, MaterialPurchase.raw_material_id == RawMaterial.id, isouter=True)
        purchases_query = purchases_query.filter(
            or_(
                RawMaterial.name.ilike(like),
                MaterialPurchase.vendor_name.ilike(like),
                MaterialPurchase.note.ilike(like),
            )
        )

    all_purchases = purchases_query.all()

    materials = []
    for material in raw_material_records:
        # Latest unit price converted to base unit (e.g. price per gr / ml)
        base_unit_price = None
        try:
            latest_purchase = (
                MaterialPurchase.query
                .filter_by(raw_material_id=material.id)
                .order_by(MaterialPurchase.purchase_date.desc(), MaterialPurchase.created_at.desc())
                .first()
            )
            if latest_purchase and latest_purchase.quantity:
                qty_in_base = convert_unit(latest_purchase.quantity, latest_purchase.unit, material.default_unit)
                if qty_in_base and qty_in_base > 0:
                    base_unit_price = int((latest_purchase.total_price or 0) / qty_in_base)
        except Exception:
            base_unit_price = None

        materials.append({
            'id': material.id,
            'code': material.id,  # استفاده از ID به عنوان کد
            'name': material.name,
            'unit': material.default_unit,
            'current_stock': material.current_stock,  # موجودی فعلی
            'min_stock': material.min_stock or 0,  # حداقل موجودی
            'base_unit_price': base_unit_price,
            'created_at': material.created_at
        })

    # محاسبه موجودی بر اساس بازه زمانی
    material_stock_by_id = calculate_material_stock_for_period(
        raw_materials=raw_material_records,
        purchases=all_purchases,
        start_date=start_date,
        end_date=end_date,
    )

    # اعمال انتقال‌ها روی موجودی انبار مرکزی (تا تاریخ پایان بازه)
    if central_wh:
        transfers_in = warehouse_transfer_sums(central_wh.id, 'in', end_date=end_date)
        transfers_out = warehouse_transfer_sums(central_wh.id, 'out', end_date=end_date)
        for rm in raw_material_records:
            base = float(material_stock_by_id.get(rm.id, 0.0) or 0.0)
            adjusted = base + float(transfers_in.get(rm.id, 0.0)) - float(transfers_out.get(rm.id, 0.0))
            material_stock_by_id[rm.id] = max(0.0, adjusted)

    total_purchase_value = db.session.query(func.coalesce(func.sum(MaterialPurchase.total_price), 0)).scalar() or 0
    distinct_vendors = db.session.query(func.count(func.distinct(MaterialPurchase.vendor_name))).scalar() or 0

    summary_cards = {
        'materials_count': len(materials),
        'total_purchase_value': int(total_purchase_value),
        'recent_purchases': len(all_purchases),
        'vendor_count': int(distinct_vendors)
    }

    return render_template(
        'admin/inventory.html',
        materials=materials,
        purchases=all_purchases,
        summary_cards=summary_cards,
        raw_material_units=RAW_MATERIAL_UNITS,
        material_stock_by_id=material_stock_by_id,
        start_date=start_date,
        end_date=end_date,
        search_query=search_query
    )


@admin_bp.route('/warehouses')
@login_required
def warehouses_management():
    """صفحه مدیریت انبارها و انتقال موجودی بین انبارها."""
    seed_warehouses_if_needed()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name.asc()).all()
    central_wh = get_central_warehouse()
    if not warehouses:
        flash('هیچ انباری تعریف نشده است.', 'warning')
        return redirect(url_for('admin.inventory_dashboard'))

    selected_id = request.args.get('warehouse_id')
    try:
        selected_id_int = int(selected_id) if selected_id else None
    except (TypeError, ValueError):
        selected_id_int = None

    selected_wh = Warehouse.query.get(selected_id_int) if selected_id_int else None
    if not selected_wh:
        selected_wh = central_wh or warehouses[0]

    show_all = (request.args.get('show_all') or '').strip() in {'1', 'true', 'yes', 'on'}

    raw_materials = RawMaterial.query.order_by(RawMaterial.name.asc()).all()
    in_sums = warehouse_transfer_sums(selected_wh.id, 'in')
    out_sums = warehouse_transfer_sums(selected_wh.id, 'out')

    rows = []
    for rm in raw_materials:
        base = float(rm.current_stock or 0) if selected_wh.code == 'central' else 0.0
        stock = max(0.0, base + float(in_sums.get(rm.id, 0.0)) - float(out_sums.get(rm.id, 0.0)))
        is_low = bool(rm.min_stock and stock <= float(rm.min_stock))
        # برای انبارهای غیر مرکزی، پیش‌فرض: فقط مواردی را نشان بده که واقعاً موجودی دارند
        if selected_wh.code != 'central' and not show_all and stock <= 0:
            continue

        rows.append({
            'id': rm.id,
            'name': rm.name,
            'unit': rm.default_unit,
            'min_stock': float(rm.min_stock or 0),
            'stock': float(stock),
            'is_low': is_low,
        })

    transfers_query = WarehouseTransfer.query.filter(
        or_(
            WarehouseTransfer.from_warehouse_id == selected_wh.id,
            WarehouseTransfer.to_warehouse_id == selected_wh.id
        )
    )
    transfers = (
        transfers_query
        .order_by(WarehouseTransfer.transfer_date.desc(), WarehouseTransfer.created_at.desc())
        .limit(200)
        .all()
    )

    low_count = sum(1 for r in rows if r.get('is_low'))

    return render_template(
        'admin/warehouses.html',
        warehouses=warehouses,
        central_wh=central_wh,
        selected_wh=selected_wh,
        raw_materials=raw_materials,
        rows=rows,
        show_all=show_all,
        low_count=low_count,
        transfers=transfers,
        raw_material_units=RAW_MATERIAL_UNITS,
        today=date.today(),
    )


@admin_bp.route('/warehouses/transfers', methods=['POST'])
@login_required
def create_warehouse_transfer():
    """ثبت انتقال موجودی بین انبارها."""
    seed_warehouses_if_needed()
    central_wh = get_central_warehouse()

    raw_material_id = request.form.get('raw_material_id')
    from_id = request.form.get('from_warehouse_id')
    to_id = request.form.get('to_warehouse_id')
    quantity_raw = (request.form.get('quantity') or '').strip()
    unit = (request.form.get('unit') or '').strip()
    note = (request.form.get('note') or '').strip() or None
    transfer_date = parse_date(request.form.get('transfer_date')) or date.today()

    try:
        raw_material_id_int = int(raw_material_id)
        from_id_int = int(from_id) if from_id else None
        to_id_int = int(to_id) if to_id else None
        quantity = float(str(quantity_raw).replace(',', '').strip())
    except (TypeError, ValueError):
        flash('اطلاعات انتقال نامعتبر است.', 'warning')
        return redirect(url_for('admin.warehouses_management'))

    if not from_id_int or not to_id_int:
        flash('مبدأ و مقصد انتقال را انتخاب کنید.', 'warning')
        return redirect(url_for('admin.warehouses_management'))

    # سیاست کسب‌وکار: انتقال‌ها فقط از انبار مرکزی انجام می‌شود
    if central_wh and from_id_int != central_wh.id:
        flash('انتقال فقط از انبار مرکزی امکان‌پذیر است.', 'warning')
        return redirect(url_for('admin.warehouses_management'))

    if from_id_int == to_id_int:
        flash('انبار مبدأ و مقصد نمی‌تواند یکسان باشد.', 'warning')
        return redirect(url_for('admin.warehouses_management'))

    if quantity <= 0:
        flash('مقدار انتقال باید بزرگتر از صفر باشد.', 'warning')
        return redirect(url_for('admin.warehouses_management'))

    rm = RawMaterial.query.get(raw_material_id_int)
    if not rm:
        flash('ماده اولیه یافت نشد.', 'warning')
        return redirect(url_for('admin.warehouses_management'))

    from_wh = Warehouse.query.get(from_id_int)
    to_wh = Warehouse.query.get(to_id_int)
    if not from_wh or not to_wh:
        flash('انبار مبدأ یا مقصد یافت نشد.', 'warning')
        return redirect(url_for('admin.warehouses_management'))

    if not unit:
        unit = rm.default_unit

    base_qty = float(convert_unit(quantity, unit, rm.default_unit))
    if base_qty <= 0:
        flash('مقدار انتقال نامعتبر است.', 'warning')
        return redirect(url_for('admin.warehouses_management'))

    available = compute_warehouse_stock_for_material(rm, from_wh, end_date=transfer_date)
    if base_qty > (available + 1e-9):
        flash(f'موجودی انبار «{from_wh.name}» برای «{rm.name}» کافی نیست.', 'warning')
        return redirect(url_for('admin.warehouses_management', warehouse_id=from_wh.id))

    transfer = WarehouseTransfer(
        raw_material_id=rm.id,
        from_warehouse_id=from_wh.id,
        to_warehouse_id=to_wh.id,
        quantity=quantity,
        unit=unit,
        base_quantity=base_qty,
        transfer_date=transfer_date,
        note=note,
        user_id=getattr(current_user, 'id', None)
    )
    db.session.add(transfer)
    try:
        db.session.commit()
        flash('انتقال با موفقیت ثبت شد.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'خطا در ثبت انتقال: {exc}', 'danger')

    return redirect(url_for('admin.warehouses_management', warehouse_id=to_wh.id))

# --- عملیات پرداخت سفارش ---
@admin_bp.route('/orders/<int:order_id>/pay', methods=['POST'])
@login_required
def pay_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'پرداخت شده':
        flash('این سفارش قبلاً پرداخت شده است.', 'warning')
        return redirect(url_for('admin.orders_report'))
    order.status = 'پرداخت شده'
    order.paid_at = datetime.utcnow()
    order.payment_method = request.form.get('payment_method', 'کارتخوان')
    db.session.commit()
    flash('سفارش با موفقیت پرداخت شد.', 'success')
    return redirect(url_for('admin.orders_report'))

# --- عملیات حذف سفارش ---
@admin_bp.route('/orders/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash('سفارش با موفقیت حذف شد.', 'success')
    return redirect(url_for('admin.orders_report'))

# --- عملیات ویرایش سفارش (فرم و ذخیره) ---
@admin_bp.route('/orders/<int:order_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    order = Order.query.get_or_404(order_id)
    if request.method == 'POST':
        order.discount = int(request.form.get('discount', 0))
        order.tax_amount = int(request.form.get('tax_amount', 0))
        order.final_amount = int(request.form.get('final_amount', 0))
        order.status = request.form.get('status', order.status)
        order.type = request.form.get('type', order.type)
        db.session.commit()
        flash('سفارش با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('admin.orders_report'))
    return render_template('admin/edit_order.html', order=order)

# --- گزارش مالی (هفتگی، ماهانه، سالانه) ---
@admin_bp.route('/financial')
@login_required
def financial_report():
    # اگر period در URL نباشد، به صورت خودکار به day redirect می‌کنیم
    if 'period' not in request.args:
        return redirect(url_for('admin.financial_report', period='day'))
    
    period = request.args.get('period', 'day')
    today = datetime.now().date()

    period_configs = {
        'day': {
            'label': 'امروز',
            'start': today,
            'description': 'عملکرد امروز و آخرین سفارش‌های ثبت‌شده'
        },
        'week': {
            'label': 'هفته جاری',
            'start': today - timedelta(days=7),
            'description': 'گزارش ۷ روز اخیر'
        },
        'month': {
            'label': 'ماه جاری',
            'start': today.replace(day=1),
            'description': 'خلاصه مالی ماه جاری'
        },
        'year': {
            'label': 'سال جاری',
            'start': today.replace(month=1, day=1),
            'description': 'گزارش سالانه برای تصمیم‌گیری‌های کلان'
        }
    }

    config = period_configs.get(period, period_configs['day'])
    period = period if period in period_configs else 'day'
    # بازه پیش‌فرض بر اساس دوره انتخابی
    start_date = config['start']
    end_date = today

    # اگر کاربر بازه دلخواه ارسال کرده باشد، آن را جایگزین می‌کنیم
    start_param = request.args.get('start')
    end_param = request.args.get('end')
    try:
        if start_param:
            start_date = datetime.strptime(start_param, '%Y-%m-%d').date()
        if end_param:
            end_date = datetime.strptime(end_param, '%Y-%m-%d').date()
    except ValueError:
        # در صورت خطای فرمت، همان بازه پیش‌فرض استفاده می‌شود
        pass

    # تبدیل تاریخ‌ها به datetime با timezone برای مقایسه صحیح
    iran_tz = pytz.timezone('Asia/Tehran')
    start_datetime = iran_tz.localize(datetime.combine(start_date, datetime.min.time()))
    end_datetime = iran_tz.localize(datetime.combine(end_date, datetime.max.time()))
    
    # استفاده از datetime با timezone برای فیلتر کردن (مطمئن‌ترین روش)
    orders = (
        Order.query
        .filter(Order.created_at >= start_datetime)
        .filter(Order.created_at <= end_datetime)
        .order_by(Order.created_at.desc())
        .all()
    )
    
    # دیباگ: چاپ اطلاعات برای بررسی
    print(f"دوره انتخابی: {period}, از {start_date} تا {end_date}")
    print(f"تعداد سفارش‌های پیدا شده: {len(orders)}")
    
    # محاسبه اطلاعات آیتم‌های حذف شده برای هر سفارش
    orders_with_deleted_info = []
    total_deleted_items_count = 0
    total_deleted_items_amount = 0
    orders_with_deleted = 0
    
    # دریافت تنظیمات برای محاسبه مالیات
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    
    for order in orders:
        deleted_items = OrderItem.query.filter_by(order_id=order.id, is_deleted=True).all()
        deleted_count = len(deleted_items)
        deleted_total = sum(item.total_price for item in deleted_items)
        orders_with_deleted_info.append({
            'order': order,
            'deleted_items_count': deleted_count,
            'deleted_items_total': deleted_total
        })
        
        # محاسبه مجموع برای باکس خلاصه
        if deleted_count > 0:
            total_deleted_items_count += deleted_count
            total_deleted_items_amount += deleted_total
            orders_with_deleted += 1
    
        # همیشه مالیات را دوباره محاسبه می‌کنیم (برای اطمینان از صحت محاسبات)
        order_items = OrderItem.query.filter_by(order_id=order.id, is_deleted=False).all()
        if order_items:
            order_items_data = [{
                'quantity': item.quantity,
                'unit_price': item.unit_price
            } for item in order_items]
            _, calculated_tax, _ = calculate_order_amount(order_items_data, order.discount or 0, tax_percent)
            # ذخیره در متغیر order برای استفاده در محاسبات (بدون commit به دیتابیس)
            order.tax_amount = calculated_tax
    
    # محاسبه مجموع‌ها
    total_sales = sum(o.final_amount or 0 for o in orders)
    total_discount = sum(o.discount or 0 for o in orders)
    total_tax = sum(o.tax_amount or 0 for o in orders)
    paid_orders = [o for o in orders if o.status == 'پرداخت شده']
    unpaid_orders = [o for o in orders if o.status == 'پرداخت نشده']
    average_ticket = int(total_sales / len(orders)) if orders else 0

    # دیباگ: چاپ محاسبات با جزئیات بیشتر
    print(f"دوره انتخابی: {period}, از {start_date} تا {end_date}")
    print(f"تعداد سفارش‌های پیدا شده: {len(orders)}")
    print(f"جمع فروش: {total_sales:,}")
    print(f"مالیات: {total_tax:,}")
    print(f"تخفیف: {total_discount:,}")
    print(f"میانگین سفارش: {average_ticket:,}")
    if orders:
        print(f"نمونه سفارش اول:")
        print(f"   - ID: {orders[0].id}")
        print(f"   - final_amount: {orders[0].final_amount}")
        print(f"   - discount: {orders[0].discount}")
        print(f"   - tax_amount: {orders[0].tax_amount}")
        print(f"   - created_at: {orders[0].created_at}")

    # استفاده از datetime با timezone برای فیلتر کردن payment_rows
    payment_rows = (
        db.session.query(
            Order.payment_method.label('method'),
            func.count(Order.id).label('count'),
            func.coalesce(func.sum(Order.final_amount), 0).label('amount')
        )
        .filter(Order.created_at >= start_datetime)
        .filter(Order.created_at <= end_datetime)
        .filter(Order.status == 'پرداخت شده')
        .group_by(Order.payment_method)
        .all()
    )

    payment_breakdown = []
    payment_buckets = {key: 0 for key in PAYMENT_BUCKET_LABELS.keys()}
    payment_bucket_counts = {key: 0 for key in PAYMENT_BUCKET_LABELS.keys()}
    for row in payment_rows:
        method_label = row.method or 'نامشخص'
        method_amount = int(row.amount or 0)
        method_count = int(row.count or 0)
        payment_breakdown.append({
            'method': method_label,
            'amount': method_amount,
            'count': method_count
        })
        bucket = categorize_payment_method(method_label)
        payment_buckets[bucket] += method_amount
        payment_bucket_counts[bucket] += method_count

    # --- Snap settlement logic (manual settlements) ---
    def _order_local_date(dt_value: datetime | None) -> date | None:
        if not dt_value:
            return None
        try:
            # created_at is usually stored with Iran tz; keep it robust for naive datetimes too.
            if dt_value.tzinfo is None:
                return dt_value.date()
            return dt_value.astimezone(iran_tz).date()
        except Exception:
            return dt_value.date()

    snap_orders = [
        o for o in paid_orders
        if categorize_payment_method(o.payment_method) == 'snap'
    ]
    snap_total = sum(o.final_amount or 0 for o in snap_orders)
    snap_count = len(snap_orders)

    # Settled periods that overlap the current report range
    settled_periods = (
        SnapSettlement.query
        .filter(SnapSettlement.start_date <= end_date)
        .filter(SnapSettlement.end_date >= start_date)
        .filter(SnapSettlement.settled_at.isnot(None))
        .all()
    )
    settled_ranges = [(s.start_date, s.end_date) for s in settled_periods]

    def _is_snap_order_settled(order: Order) -> bool:
        od = _order_local_date(order.created_at)
        if not od:
            return False
        for s_start, s_end in settled_ranges:
            if s_start <= od <= s_end:
                return True
        return False

    snap_settled_total = sum((o.final_amount or 0) for o in snap_orders if _is_snap_order_settled(o))
    snap_settled_count = sum(1 for o in snap_orders if _is_snap_order_settled(o))
    snap_pending_total = max(0, snap_total - snap_settled_total)
    snap_pending_count = max(0, snap_count - snap_settled_count)

    current_snap_settlement = (
        SnapSettlement.query
        .filter(SnapSettlement.start_date == start_date)
        .filter(SnapSettlement.end_date == end_date)
        .order_by(SnapSettlement.settled_at.desc())
        .first()
    )
    snap_current_range_settled = bool(current_snap_settlement and current_snap_settlement.settled_at)

    closing_summary = {
        'pos_total': payment_buckets.get('pos', 0),
        'pos_count': payment_bucket_counts.get('pos', 0),
        'transfer_total': payment_buckets.get('card_to_card', 0),
        'transfer_count': payment_bucket_counts.get('card_to_card', 0),
        'paid_total': sum(o.final_amount or 0 for o in paid_orders),
        'pending_total': sum(o.final_amount or 0 for o in unpaid_orders)
    }
    closing_summary['drawer_expected'] = closing_summary['pos_total']
    closing_summary['snap_total'] = snap_total
    closing_summary['snap_count'] = snap_count
    closing_summary['snap_settled_total'] = snap_settled_total
    closing_summary['snap_settled_count'] = snap_settled_count
    closing_summary['snap_pending_total'] = snap_pending_total
    closing_summary['snap_pending_count'] = snap_pending_count
    # Net "received" total: paid orders minus snap that is not yet settled
    closing_summary['received_total'] = max(0, closing_summary['paid_total'] - snap_pending_total)

    payment_breakdown_display = [
        {
            'label': PAYMENT_BUCKET_LABELS[bucket],
            'amount': payment_buckets.get(bucket, 0),
            'count': payment_bucket_counts.get(bucket, 0)
        }
        for bucket in PAYMENT_BUCKET_LABELS.keys()
    ]

    channel_totals = defaultdict(lambda: {'amount': 0, 'count': 0})
    for order in paid_orders:
        channel_key = order.type or 'حضوری'
        channel_totals[channel_key]['amount'] += order.final_amount or 0
        channel_totals[channel_key]['count'] += 1
    channel_breakdown = [
        {'label': label, 'amount': stats['amount'], 'count': stats['count']}
        for label, stats in channel_totals.items()
    ]

    period_options = [
        {'key': 'day', 'label': 'امروز', 'hint': 'نمای لحظه‌ای'},
        {'key': 'week', 'label': 'هفته جاری', 'hint': '۷ روز اخیر'},
        {'key': 'month', 'label': 'ماه جاری', 'hint': 'شروع ماه تا امروز'},
        {'key': 'year', 'label': 'سال جاری', 'hint': 'از ابتدای سال'},
    ]

    return render_template('admin/financial_report.html',
                           orders=orders,
                           orders_with_deleted_info=orders_with_deleted_info,
                           total_sales=total_sales,
                           total_discount=total_discount,
                           total_tax=total_tax,
                           paid_orders=paid_orders,
                           unpaid_orders=unpaid_orders,
                           payment_breakdown=payment_breakdown_display,
                           closing_summary=closing_summary,
                           channel_breakdown=channel_breakdown,
                           average_ticket=average_ticket,
                           period=period,
                           period_label=config['label'],
                           total_deleted_items_count=total_deleted_items_count,
                           total_deleted_items_amount=total_deleted_items_amount,
                           orders_with_deleted=orders_with_deleted,
                           period_description=config.get('description', ''),
                           period_options=period_options,
                           start_date=start_date,
                           end_date=end_date,
                           snap_current_range_settled=snap_current_range_settled,
                           snap_current_settlement=current_snap_settlement)


@admin_bp.route('/financial/snap/settle', methods=['POST'])
@login_required
def settle_snap():
    """
    Mark Snap settlements as settled for a given date range.
    This does NOT change order statuses; it only affects financial report calculations.
    """
    start_date = parse_date(request.form.get('start'))
    end_date = parse_date(request.form.get('end'))
    period = (request.form.get('period') or 'day').strip() or 'day'

    if not start_date or not end_date or end_date < start_date:
        flash('بازه انتخاب‌شده برای تسویه اسنپ نامعتبر است.', 'warning')
        return redirect(url_for('admin.financial_report', period=period))

    settlement = SnapSettlement.query.filter_by(start_date=start_date, end_date=end_date).first()
    if not settlement:
        settlement = SnapSettlement(
            start_date=start_date,
            end_date=end_date,
            created_at=datetime.now(pytz.timezone('Asia/Tehran')),
            user_id=getattr(current_user, 'id', None)
        )
        db.session.add(settlement)

    settlement.settled_at = datetime.utcnow()
    settlement.user_id = getattr(current_user, 'id', None)

    try:
        db.session.commit()
        flash('تسویه اسنپ برای این بازه ثبت شد.', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'خطا در ثبت تسویه اسنپ: {exc}', 'danger')

    return redirect(url_for(
        'admin.financial_report',
        period=period,
        start=start_date.isoformat(),
        end=end_date.isoformat()
    ))

# --- مدیریت کاربران (لیست، افزودن، ویرایش، حذف) ---
@admin_bp.route('/users')
@login_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users, role_definitions=USER_ROLE_DEFINITIONS)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        name = (request.form.get('name') or '').strip() or None
        role = (request.form.get('role', 'waiter') or 'waiter').strip()
        phone = (request.form.get('phone') or '').strip() or None

        if not username or not password:
            flash('نام کاربری و رمز عبور الزامی است.', 'danger')
            return redirect(url_for('admin.add_user'))

        if len(password) < 6:
            flash('رمز عبور باید حداقل ۶ کاراکتر باشد.', 'danger')
            return redirect(url_for('admin.add_user'))

        if User.query.filter_by(username=username).first():
            flash('این نام کاربری قبلاً ثبت شده است.', 'danger')
            return redirect(url_for('admin.add_user'))
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            name=name,
            role=role,
            phone=phone,
            created_at=datetime.now(pytz.timezone("Asia/Tehran")),
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        flash('کاربر جدید با موفقیت اضافه شد.', 'success')
        return redirect(url_for('admin.users_list'))
    return render_template('admin/add_user.html', roles=USER_ROLE_DEFINITIONS)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.name = request.form.get('name', user.name)
        user.role = request.form.get('role', user.role)
        user.phone = request.form.get('phone', user.phone)
        db.session.commit()
        flash('اطلاعات کاربر ویرایش شد.', 'success')
        return redirect(url_for('admin.users_list'))
    return render_template('admin/edit_user.html', user=user, roles=USER_ROLE_DEFINITIONS)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('کاربر حذف شد.', 'success')
    return redirect(url_for('admin.users_list'))

# --- جستجوی سریع سفارش بر اساس شماره فاکتور یا نام مشتری (AJAX) ---
@admin_bp.route('/orders/search')
@login_required
def search_orders():
    q = request.args.get('q')
    if not q:
        return jsonify([])
    try:
        q_int = int(q)
    except (TypeError, ValueError):
        q_int = None

    filters = [
        (Order.invoice_number == q),
        (Order.invoice_uid == q),
        (Customer.name.ilike(f'%{q}%')),
        (Customer.phone.ilike(f'%{q}%'))
    ]
    if q_int is not None:
        filters.append(Order.daily_sequence == q_int)

    orders = Order.query.join(Customer).filter(or_(*filters)).all()
    results = []
    for o in orders:
        results.append({
            'id': o.id,
            'invoice_uid': o.invoice_uid,
            'invoice_number': o.invoice_number,
            'daily_invoice_number': o.daily_sequence,
            'customer': o.customer.name,
            'status': o.status,
            'final_amount': o.final_amount,
            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M')
        })
    return jsonify(results)

# --- پروفایل کاربر ---
@admin_bp.route('/profile')
@login_required
def profile():
    user = current_user
    return render_template('admin/profile.html', user=user)

@admin_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = current_user
    if request.method == 'POST':
        user.name = request.form.get('name', user.name)
        user.phone = request.form.get('phone', user.phone)
        db.session.commit()
        flash('پروفایل شما به‌روزرسانی شد.', 'success')
        return redirect(url_for('admin.profile'))
    return render_template('admin/edit_profile.html', user=user)

# --- خروج از حساب کاربری ---
@admin_bp.route('/logout')
@login_required
def logout():
    from flask_login import logout_user
    logout_user()
    flash('با موفقیت خارج شدید.', 'info')
    return redirect(url_for('menu.index'))

# --- خطای دسترسی ---
@admin_bp.app_errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

# --- خطای پیدا نشدن ---
@admin_bp.app_errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

# --- خطای سرور ---
@admin_bp.app_errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

from flask import render_template
from flask_login import login_required
from models.models import Order

@admin_bp.route('/orders/<int:order_id>/invoice')
@login_required
def invoice(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('invoice.html', order=order)

@admin_bp.route('/inventory/raw-materials', methods=['POST'])
@login_required
def create_raw_material():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'status': 'error', 'message': 'نام ماده اولیه الزامی است.'}), 400

    default_unit = (data.get('unit') or 'gr').strip()
    min_stock = data.get('min_stock')
    
    # تبدیل min_stock به float
    try:
        min_stock = float(min_stock) if min_stock else None
    except (ValueError, TypeError):
        min_stock = None

    existing = RawMaterial.query.filter_by(name=name).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'این ماده اولیه قبلاً ثبت شده است.'}), 400

    material = RawMaterial(name=name, default_unit=default_unit, min_stock=min_stock)
    db.session.add(material)
    db.session.commit()
    return jsonify({'status': 'success', 'material': {'id': material.id, 'name': material.name, 'unit': material.default_unit}})

@admin_bp.route('/inventory/raw-materials/<int:material_id>', methods=['PUT'])
@login_required
def update_raw_material(material_id):
    material = RawMaterial.query.get_or_404(material_id)
    data = request.get_json() or {}
    
    name = (data.get('name') or '').strip()
    default_unit = (data.get('unit') or 'gr').strip()
    min_stock = data.get('min_stock')
    
    if not name:
        return jsonify({'status': 'error', 'message': 'نام ماده اولیه الزامی است.'}), 400
    
    # تبدیل min_stock به float
    try:
        min_stock = float(min_stock) if min_stock else None
    except (ValueError, TypeError):
        min_stock = None
    
    # بررسی تکراری بودن نام (به جز خود ماده)
    existing = RawMaterial.query.filter(RawMaterial.name == name, RawMaterial.id != material_id).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'ماده اولیه با این نام قبلاً ثبت شده است.'}), 400
    
    material.name = name
    material.default_unit = default_unit
    material.min_stock = min_stock
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'ماده اولیه با موفقیت به‌روزرسانی شد.'})

@admin_bp.route('/inventory/raw-materials/<int:material_id>', methods=['DELETE'])
@login_required
def delete_raw_material(material_id):
    material = RawMaterial.query.get_or_404(material_id)
    
    # بررسی تمام وابستگی‌ها
    dependencies = []
    
    # 1. بررسی خریدها
    purchases = MaterialPurchase.query.filter_by(raw_material_id=material_id).all()
    if purchases:
        dependencies.append({
            'type': 'خریدها',
            'count': len(purchases),
            'items': [f"خرید {p.id} ({p.purchase_date})" for p in purchases[:5]]  # فقط 5 تا اول
        })
    
    # 2. بررسی مصرف‌ها
    usages = RawMaterialUsage.query.filter_by(raw_material_id=material_id).all()
    if usages:
        dependencies.append({
            'type': 'مصرف‌ها',
            'count': len(usages),
            'items': [f"مصرف {u.id}" for u in usages[:5]]
        })
    
    # 3. بررسی انتقال‌ها
    transfers = WarehouseTransfer.query.filter_by(raw_material_id=material_id).all()
    if transfers:
        dependencies.append({
            'type': 'انتقال‌های انبار',
            'count': len(transfers),
            'items': [f"انتقال {t.id}" for t in transfers[:5]]
        })
    
    # 4. بررسی ارتباط با منو
    menu_materials = MenuItemMaterial.query.filter_by(raw_material_id=material_id).all()
    if menu_materials:
        menu_items = []
        for mm in menu_materials[:5]:
            menu_item_name = mm.menu_item.name if mm.menu_item else f"آیتم {mm.menu_item_id}"
            menu_items.append(f"{menu_item_name}")
        dependencies.append({
            'type': 'آیتم‌های منو',
            'count': len(menu_materials),
            'items': menu_items
        })
    
    # اگر وابستگی وجود دارد، اجازه حذف نده
    if dependencies:
        # ساخت پیام کامل
        messages = []
        for dep in dependencies:
            items_text = '، '.join(dep['items'])
            if dep['count'] > 5:
                items_text += f" و {dep['count'] - 5} مورد دیگر"
            messages.append(f"{dep['type']}: {dep['count']} مورد ({items_text})")
        
        message = f"این ماده اولیه «{material.name}» به موارد زیر وابسته است:\n\n" + "\n".join(messages)
        message += "\n\nلطفاً ابتدا تمام وابستگی‌ها را حذف کنید و سپس دوباره تلاش کنید."
        
        return jsonify({
            'status': 'error',
            'message': message,
            'dependencies': dependencies
        }), 400
    
    # اگر وابستگی وجود ندارد، اجازه حذف بده
    # حذف خریدهای مرتبط (اگر چیزی باقی مانده باشد)
    MaterialPurchase.query.filter_by(raw_material_id=material_id).delete()
    
    # حذف مصرف‌های مرتبط
    RawMaterialUsage.query.filter_by(raw_material_id=material_id).delete()
    
    # حذف انتقال‌های مرتبط
    WarehouseTransfer.query.filter_by(raw_material_id=material_id).delete()
    
    # حذف ارتباط با منو
    MenuItemMaterial.query.filter_by(raw_material_id=material_id).delete()
    
    # حذف خود ماده اولیه
    db.session.delete(material)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': f'ماده اولیه «{material.name}» با موفقیت حذف شد.'})

@admin_bp.route('/inventory/purchases', methods=['POST'])
@login_required
def create_material_purchase():
    data = request.get_json() or {}
    raw_material_id = data.get('raw_material_id')
    raw_material = RawMaterial.query.get(raw_material_id)
    if not raw_material:
        return jsonify({'status': 'error', 'message': 'ماده اولیه انتخاب شده یافت نشد.'}), 404

    quantity = data.get('quantity')
    total_price = data.get('total_price')
    unit = (data.get('unit') or raw_material.default_unit).strip()
    vendor_name = (data.get('vendor_name') or '').strip() or None
    vendor_phone = (data.get('vendor_phone') or '').strip() or None
    note = (data.get('note') or '').strip() or None
    purchase_date = data.get('purchase_date')

    try:
        quantity = float(str(quantity).replace(',', '').strip())
    except (TypeError, ValueError):
        quantity = 0

    try:
        total_price = int(float(str(total_price).replace(',', '').strip()))
    except (TypeError, ValueError):
        total_price = 0

    from utils.helpers import parse_jalali_date
    parsed_date = parse_jalali_date(purchase_date) if purchase_date else datetime.now().date()

    purchase = MaterialPurchase(
        raw_material_id=raw_material.id,
        purchase_date=parsed_date,
        quantity=quantity,
        unit=unit,
        total_price=total_price,
        vendor_name=vendor_name,
        vendor_phone=vendor_phone,
        note=note
    )
    db.session.add(purchase)
    db.session.commit()
    return jsonify({'status': 'success'})

@admin_bp.route('/inventory/purchases/<int:purchase_id>', methods=['PUT'])
@login_required
def update_material_purchase(purchase_id):
    purchase = MaterialPurchase.query.get_or_404(purchase_id)
    data = request.get_json() or {}
    
    raw_material_id = data.get('raw_material_id')
    raw_material = RawMaterial.query.get(raw_material_id)
    if not raw_material:
        return jsonify({'status': 'error', 'message': 'ماده اولیه انتخاب شده یافت نشد.'}), 404
    
    quantity = data.get('quantity')
    total_price = data.get('total_price')
    unit = (data.get('unit') or raw_material.default_unit).strip()
    vendor_name = (data.get('vendor_name') or '').strip() or None
    vendor_phone = (data.get('vendor_phone') or '').strip() or None
    note = (data.get('note') or '').strip() or None
    purchase_date_str = data.get('purchase_date')
    
    try:
        quantity = float(str(quantity).replace(',', '').strip())
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'مقدار نامعتبر است.'}), 400
    
    try:
        total_price = int(float(str(total_price).replace(',', '').strip()))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'قیمت نامعتبر است.'}), 400
    
    from utils.helpers import parse_jalali_date
    from datetime import datetime
    if purchase_date_str:
        # اگر تاریخ به صورت YYYY-MM-DD باشد (از input type="date")
        try:
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        except ValueError:
            purchase_date = parse_jalali_date(purchase_date_str)
    else:
        purchase_date = purchase.purchase_date
    
    purchase.raw_material_id = raw_material.id
    purchase.purchase_date = purchase_date
    purchase.quantity = quantity
    purchase.unit = unit
    purchase.total_price = total_price
    purchase.vendor_name = vendor_name
    purchase.vendor_phone = vendor_phone
    purchase.note = note
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'خرید با موفقیت به‌روزرسانی شد.'})

@admin_bp.route('/inventory/purchases/<int:purchase_id>', methods=['DELETE'])
@login_required
def delete_material_purchase(purchase_id):
    purchase = MaterialPurchase.query.get_or_404(purchase_id)
    db.session.delete(purchase)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'خرید با موفقیت حذف شد.'})


@admin_bp.route('/inventory/clear-all', methods=['DELETE', 'POST'])
@login_required
def clear_all_inventory_data():
    """حذف تمام داده‌های انبار - مستقیماً با SQL برای اطمینان از حذف کامل"""
    try:
        # استفاده از SQL خام برای اطمینان از حذف کامل
        engine = db.get_engine()
        
        with engine.begin() as conn:
            # شمارش قبل از حذف
            result = conn.execute(text('SELECT COUNT(*) FROM raw_material'))
            before_count = result.scalar()
            
            # حذف با SQL خام (مستقیماً در دیتابیس)
            conn.execute(text('DELETE FROM raw_material_usage'))
            conn.execute(text('DELETE FROM warehouse_transfer'))
            conn.execute(text('DELETE FROM material_purchase'))
            conn.execute(text('DELETE FROM menu_item_material'))
            conn.execute(text('DELETE FROM raw_material'))
        
        # Commit تغییرات
        db.session.commit()
        
        # بررسی نهایی
        final_count = RawMaterial.query.count()
        
        if final_count == 0:
            flash(f'تمام داده‌های انبار ({before_count} ماده اولیه) با موفقیت حذف شدند.', 'success')
            return jsonify({'status': 'success', 'message': f'تمام داده‌های انبار ({before_count} ماده اولیه) با موفقیت حذف شدند.'})
        else:
            flash(f'هشدار: {final_count} ماده اولیه هنوز باقی مانده است.', 'warning')
            return jsonify({'status': 'warning', 'message': f'هشدار: {final_count} ماده اولیه هنوز باقی مانده است.'}), 200
        
    except Exception as e:
        db.session.rollback()
        flash(f'خطا در حذف داده‌ها: {str(e)}', 'danger')
        return jsonify({'status': 'error', 'message': f'خطا در حذف داده‌ها: {str(e)}'}), 500
