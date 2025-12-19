from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from models.models import db, Category, MenuItem, MenuItemMaterial, RawMaterial, MaterialPurchase, Order, OrderItem, CostFormulaSettings
from flask_login import login_required
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import math

menu_bp = Blueprint('menu', __name__)
MATERIAL_UNITS = ['عدد', 'گرم', 'میلی‌لیتر', 'کیلوگرم', 'لیتر', 'بسته', 'متر']

UNIT_LABELS = {
    'عدد': 'عدد',
    'unit': 'عدد',
    'عددی': 'عدد',
    'pcs': 'عدد',
    'piece': 'عدد',
    'gr': 'گرم',
    'g': 'گرم',
    'گرم': 'گرم',
    'kg': 'کیلوگرم',
    'کیلوگرم': 'کیلوگرم',
    'میلی‌لیتر': 'میلی‌لیتر',
    'ml': 'میلی‌لیتر',
    'mililiter': 'میلی‌لیتر',
    'لیتر': 'لیتر',
    'liter': 'لیتر',
    'l': 'لیتر',
    'بسته': 'بسته',
    'package': 'بسته',
    'pack': 'بسته',
    'm': 'متر',
    'meter': 'متر',
    'متر': 'متر'
}


def normalize_unit(value):
    if not value:
        return 'عدد'
    val = str(value).strip()
    for key, label in UNIT_LABELS.items():
        if val.lower() == key.lower():
            return label
    return val

@menu_bp.route('/menu')
@login_required
def show_menu():
    # دریافت همه دسته‌بندی‌ها و آیتم‌های منو
    categories = Category.query.filter_by(is_active=True).order_by(Category.order, Category.name).all()
    menu_items = MenuItem.query.filter_by(is_active=True).order_by(MenuItem.name).all()

    # --- Popularity (محبوبیت) بر اساس تعداد سفارش‌های پرداخت‌شده ---
    # معیار: تعداد سفارش‌هایی که آیتم در آنها بوده (count distinct orders)
    # tie-breaker: مجموع تعداد فروش (sum quantity)
    # استفاده از == 0 برای SQLite به جای is_(False)
    popularity_rows = (
        db.session.query(
            OrderItem.menu_item_id.label('menu_item_id'),
            func.count(func.distinct(OrderItem.order_id)).label('orders_count'),
            func.coalesce(func.sum(OrderItem.quantity), 0).label('quantity_sold')
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status == 'پرداخت شده')
        .filter(or_(OrderItem.is_deleted == False, OrderItem.is_deleted == None))
        .group_by(OrderItem.menu_item_id)
        .all()
    )
    popularity = {
        int(row.menu_item_id): {
            'orders_count': int(row.orders_count or 0),
            'quantity_sold': int(row.quantity_sold or 0),
        }
        for row in popularity_rows
        if row and row.menu_item_id is not None
    }
    
    # گروه‌بندی آیتم‌ها بر اساس دسته‌بندی
    items_by_category = {}
    items_without_category = []
    
    for item in menu_items:
        if item.category_id:
            category_id = item.category_id
            if category_id not in items_by_category:
                items_by_category[category_id] = []
            items_by_category[category_id].append(item)
        else:
            items_without_category.append(item)

    def popularity_sort_key(item: MenuItem):
        stats = popularity.get(int(item.id), {'orders_count': 0, 'quantity_sold': 0})
        # sort desc by orders_count, desc by quantity_sold, then name asc
        return (-stats['orders_count'], -stats['quantity_sold'], (item.name or '').strip())

    # مرتب‌سازی آیتم‌ها داخل هر دسته بر اساس محبوبیت
    for cat_id, items in items_by_category.items():
        items_by_category[cat_id] = sorted(items, key=popularity_sort_key)
    items_without_category = sorted(items_without_category, key=popularity_sort_key)
    
    # ساخت لیست گروه‌بندی شده
    grouped_items = []
    
    # اول دسته‌بندی‌های مرتب شده
    for category in categories:
        if category.id in items_by_category:
            grouped_items.append({
                'category': category,
                'items': items_by_category[category.id]
            })
    
    # سپس آیتم‌های بدون دسته‌بندی
    if items_without_category:
        grouped_items.append({
            'category': None,
            'items': items_without_category
        })
    
    return render_template('menu/menu.html', 
                         categories=categories, 
                         menu_items=menu_items, 
                         grouped_items=grouped_items,
                         sorted_items_by_category=items_by_category,
                         popularity=popularity,
                         material_units=MATERIAL_UNITS)

@menu_bp.route('/menu/api/categories')
@login_required
def get_categories_api():
    """API endpoint برای دریافت آیتم‌های منو با دسته‌بندی‌ها"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.order, Category.name).all()
    menu_items = MenuItem.query.filter_by(is_active=True).order_by(MenuItem.name).all()
    
    # گروه‌بندی آیتم‌ها بر اساس دسته‌بندی
    categories_data = []
    
    for category in categories:
        category_items = [item for item in menu_items if item.category_id == category.id]
        if category_items:
            items_data = []
            for item in category_items:
                items_data.append({
                    'id': item.id,
                    'name': item.name,
                    'price': item.price,
                    'stock': item.stock
                })
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'items': items_data
            })
    
    # آیتم‌های بدون دسته‌بندی
    items_without_category = [item for item in menu_items if not item.category_id]
    if items_without_category:
        items_data = []
        for item in items_without_category:
            items_data.append({
                'id': item.id,
                'name': item.name,
                'price': item.price,
                'stock': item.stock
            })
        categories_data.append({
            'id': 0,
            'name': 'بدون دسته‌بندی',
            'items': items_data
        })
    
    return jsonify({'success': True, 'categories': categories_data})


@menu_bp.route('/menu/price-management')
@login_required
def menu_price_management():
    """مدیریت قیمت منو - نمایش قیمت تمام‌شده بر اساس مواد اولیه مصرفی"""
    menu_items = MenuItem.query.filter_by(is_active=True).order_by(MenuItem.name).all()
    
    category_total_cost = 0
    items_data = []
    
    for item in menu_items:
        item_total_cost = 0
        materials_data = []
        
        # دریافت مواد اولیه مصرفی این آیتم
        item_materials = MenuItemMaterial.query.filter_by(menu_item_id=item.id).all()
        
        for item_material in item_materials:
            raw_material = item_material.raw_material
            if not raw_material:
                continue
            
            # محاسبه قیمت تمام‌شده ماده اولیه
            # میانگین قیمت واحد از آخرین خریدها
            purchases = MaterialPurchase.query.filter_by(
                raw_material_id=raw_material.id
            ).order_by(
                MaterialPurchase.purchase_date.desc(),
                MaterialPurchase.created_at.desc()
            ).limit(10).all()  # آخرین 10 خرید
            
            if purchases:
                # محاسبه میانگین قیمت واحد
                total_price = sum(p.unit_price for p in purchases if p.unit_price > 0)
                avg_unit_price = total_price / len([p for p in purchases if p.unit_price > 0]) if purchases else 0
            else:
                avg_unit_price = 0
            
            # تبدیل واحد ماده اولیه به واحد مصرفی در آیتم منو
            # اینجا فرض می‌کنیم که واحدها یکسان هستند (نیاز به تبدیل واحد دارد)
            quantity_value = item_material.quantity_value
            if quantity_value is None:
                quantity_value = 0
            
            material_cost = quantity_value * avg_unit_price
            item_total_cost += material_cost
            
            materials_data.append({
                'name': raw_material.name,
                'quantity': quantity_value,
                'unit': item_material.unit,
                'avg_unit_price': avg_unit_price,
                'total_cost': material_cost
            })
        
        category_total_cost += item_total_cost
        
        # پیشنهاد اولیه قیمت فروش بر اساس بهای مواد + سربار هر سفارش
        suggested_price_raw = item_total_cost  # هزینه متریال

        items_data.append({
            'id': item.id,
            'name': item.name,
            'selling_price': item.price,
            'cost_price': item_total_cost,
            'profit': item.price - item_total_cost,
            'profit_margin': ((item.price - item_total_cost) / item.price * 100) if item.price > 0 else 0,
            'materials': materials_data
        })
    
    categories_data = [{
        'id': 0,
        'name': 'همه آیتم‌ها',
        'total_cost': category_total_cost,
        'items': items_data
    }]

    # محاسبه میانگین تعداد سفارشات و میانگین مبلغ هر سفارش در حدود یک ماه اخیر
    # بارگذاری تنظیمات قبلی فرمول، اگر وجود داشته باشد
    formula = CostFormulaSettings.query.first()

    # محاسبه میانگین تعداد سفارشات و میانگین مبلغ هر سفارش در حدود یک ماه اخیر (فقط برای پیشنهاد اولیه)
    monthly_orders_avg = formula.monthly_orders_avg if formula else 0
    avg_order_price = formula.avg_order_price if formula else 0
    cost_control_percent = formula.cost_control_percent if formula else 0

    if monthly_orders_avg == 0 or avg_order_price == 0:
        try:
            last_30_days = datetime.utcnow() - timedelta(days=30)
            recent_orders = Order.query.filter(
                Order.created_at >= last_30_days,
                Order.status == 'پرداخت شده'
            ).all()

            orders_count = len(recent_orders)
            total_final = sum(o.final_amount for o in recent_orders) if recent_orders else 0
            if orders_count > 0:
                monthly_orders_avg = monthly_orders_avg or orders_count
                avg_order_price = avg_order_price or int(total_final / orders_count)
        except Exception:
            pass

    # محاسبه هزینه‌های ثابت و سهم سرانه هر سفارش
    total_fixed_cost = 0
    staff_cost = 0
    rent_cost = 0
    depreciation_cost = 0

    if formula:
        staff_cost = formula.total_staff_salary or 0
        depreciation_cost = formula.depreciation or 0
        rent_cost = (formula.rent_amount or 0) if formula.has_rent else 0
        total_fixed_cost = staff_cost + depreciation_cost + rent_cost

    per_order_overhead = int(total_fixed_cost / monthly_orders_avg) if monthly_orders_avg else 0

    # اعمال قیمت پیشنهادی گرد شده (ضریب ۵۰۰۰ تومان، رو به بالا) برای هر آیتم
    # شامل درصد کاست کنترل روی هزینه‌ها و بازه حداقل/حداکثر قیمت
    for cat in categories_data:
        for item in cat['items']:
            base_cost = (item['cost_price'] or 0) + per_order_overhead
            # اعمال درصد کاست کنترل (مثلاً ۱۰٪ افزایش روی هزینه‌ها)
            if cost_control_percent:
                base_suggested = base_cost * (1 + (cost_control_percent / 100.0))
            else:
                base_suggested = base_cost
            # حداقل قیمت پیشنهادی (بدون کاست کنترل، اما گرد شده روی ۵۰۰۰)
            if base_cost > 0:
                min_price = int(math.ceil(base_cost / 5000.0) * 5000)
            else:
                min_price = 0

            if base_suggested <= 0:
                rounded_suggested = 0
            else:
                rounded_suggested = int(math.ceil(base_suggested / 5000.0) * 5000)
            item['suggested_price'] = rounded_suggested
            item['min_price'] = min_price

    return render_template(
        'menu/price_management.html',
        categories=categories_data,
        monthly_orders_avg=monthly_orders_avg,
        avg_order_price=avg_order_price,
        cost_control_percent=cost_control_percent,
        formula=formula,
        total_fixed_cost=total_fixed_cost,
        staff_cost=staff_cost,
        rent_cost=rent_cost,
        depreciation_cost=depreciation_cost,
        per_order_overhead=per_order_overhead,
    )


@menu_bp.route('/menu/cost-formula-settings', methods=['POST'])
@login_required
def save_cost_formula_settings():
    """ذخیره تنظیمات فرمول بهای تمام‌شده از مودال مدیریت قیمت منو"""
    data = request.get_json() or {}

    personnel_data = data.get('personnel') or []
    # محاسبه تعداد پرسنل و مجموع حقوق از روی لیست
    staff_count = 0
    total_staff_salary = 0
    normalized_personnel = []
    for p in personnel_data:
        name = (p.get('name') or '').strip()
        salary = int(p.get('salary') or 0)
        if not name and salary <= 0:
            continue
        staff_count += 1
        total_staff_salary += salary
        normalized_personnel.append({'name': name, 'salary': salary})
    has_rent = bool(data.get('has_rent'))
    rent_amount = int(data.get('rent_amount') or 0)
    depreciation = int(data.get('depreciation') or 0)
    monthly_orders_avg = int(data.get('monthly_orders_avg') or 0)
    avg_order_price = int(data.get('avg_order_price') or 0)
    cost_control_percent = int(data.get('cost_control_percent') or 0)

    formula = CostFormulaSettings.query.first()
    if not formula:
        formula = CostFormulaSettings()
        db.session.add(formula)

    formula.staff_count = staff_count
    formula.total_staff_salary = total_staff_salary
    formula.personnel = normalized_personnel
    formula.has_rent = has_rent
    formula.rent_amount = rent_amount if has_rent else 0
    formula.depreciation = depreciation
    formula.monthly_orders_avg = monthly_orders_avg
    formula.avg_order_price = avg_order_price
    formula.cost_control_percent = cost_control_percent

    db.session.commit()

    return jsonify({'status': 'success'})


@menu_bp.route('/menu/calculate-order-stats', methods=['GET'])
@login_required
def calculate_order_stats():
    """محاسبه میانگین تعداد سفارشات و میانگین مبلغ هر سفارش از سفارشات موجود"""
    try:
        last_30_days = datetime.utcnow() - timedelta(days=30)
        recent_orders = Order.query.filter(
            Order.created_at >= last_30_days,
            Order.status == 'پرداخت شده'
        ).all()

        orders_count = len(recent_orders)
        total_final = sum(o.final_amount for o in recent_orders) if recent_orders else 0
        
        if orders_count > 0:
            monthly_orders_avg = orders_count
            avg_order_price = int(total_final / orders_count)
        else:
            monthly_orders_avg = 0
            avg_order_price = 0

        return jsonify({
            'status': 'success',
            'monthly_orders_avg': monthly_orders_avg,
            'avg_order_price': avg_order_price
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'خطا در محاسبه: {str(e)}'
        }), 500

@menu_bp.route('/menu/item/<int:item_id>/apply-suggested-price', methods=['POST'])
@login_required
def apply_suggested_price(item_id):
    """به‌روزرسانی قیمت آیتم منو بر اساس قیمت پیشنهادی (ارسالی از فرانت)."""
    data = request.get_json() or {}
    try:
        new_price = int(data.get('price') or 0)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'قیمت نامعتبر است.'}), 400

    if new_price <= 0:
        return jsonify({'status': 'error', 'message': 'قیمت پیشنهادی معتبر نیست.'}), 400

    item = MenuItem.query.get_or_404(item_id)
    item.price = new_price
    db.session.commit()

    return jsonify({'status': 'success', 'price': new_price})

# Note: The following add/edit routes seem to be form-based, not JSON API based.
# The JSON API routes like /save, /category/save, etc., are handled separately below.


@menu_bp.route('/menu/item/add', methods=['GET', 'POST'])
@login_required
def add_menu_item():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        stock = request.form.get('stock')
        
        if not name or not price:
            flash('نام و قیمت الزامی هستند.', 'danger')
            return redirect(url_for('menu.add_menu_item'))
        
        try:
            price = int(price)
            stock = int(stock) if stock else 0
        except ValueError:
            flash('مقدار عددی نامعتبر است.', 'danger')
            return redirect(url_for('menu.add_menu_item'))
        
        menu_item = MenuItem(name=name, price=price, stock=stock)
        db.session.add(menu_item)
        db.session.commit()
        
        flash('آیتم جدید با موفقیت اضافه شد.', 'success')
        return redirect(url_for('menu.show_menu'))
    
    return render_template('menu/add_menu_item.html')

@menu_bp.route('/menu/item/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(id):
    menu_item = MenuItem.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        stock = request.form.get('stock')
        
        if not name or not price:
            flash('نام و قیمت الزامی هستند.', 'danger')
            return redirect(url_for('menu.edit_menu_item', id=id))
        
        try:
            price = int(price)
            stock = int(stock) if stock else 0
        except ValueError:
            flash('مقدار عددی نامعتبر است.', 'danger')
            return redirect(url_for('menu.edit_menu_item', id=id))
        
        menu_item.name = name
        menu_item.price = price
        menu_item.stock = stock
        db.session.commit()
        
        flash('آیتم با موفقیت به‌روزرسانی شد.', 'success')
        return redirect(url_for('menu.show_menu'))
    
    return render_template('menu/edit_menu_item.html', menu_item=menu_item)

@menu_bp.route('/menu/search')
@login_required
def search_menu():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    items = MenuItem.query.filter(
        MenuItem.name.contains(query),
        MenuItem.is_active == True
    ).limit(10).all()
    
    results = [{'id': item.id, 'name': item.name, 'price': item.price} for item in items]
    return jsonify(results)

@menu_bp.route('/menu/item/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    item.is_active = False  # فقط غیرفعال می‌کنیم
    db.session.commit()
    return jsonify({'success': True, 'status': 'success', 'message': 'آیتم با موفقیت غیرفعال شد.'})

@menu_bp.route('/menu/save', methods=['POST'])
@login_required
def save_menu_item_json():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    item_id = data.get('id')
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock')
    
    if not name or not price:
        return jsonify({'status': 'error', 'message': 'نام و قیمت الزامی هستند'}), 400
    
    try:
        price = int(price) if price else 0
        # اگر stock خالی است یا None است، به 0 تبدیل می‌شود
        stock = int(stock) if stock and str(stock).strip() else 0
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'مقدار عددی نامعتبر است'}), 400
    
    category_id = data.get('category_id')
    
    # اگر category_id وجود ندارد یا دسته‌بندی وجود ندارد، یک دسته‌بندی پیش‌فرض ایجاد کن
    if not category_id:
        # بررسی وجود دسته‌بندی پیش‌فرض
        default_category = Category.query.filter_by(name='عمومی').first()
        if not default_category:
            default_category = Category(
                name='عمومی',
                description='دسته‌بندی پیش‌فرض',
                order=0,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(default_category)
            db.session.flush()  # برای گرفتن ID
        category_id = default_category.id
    else:
        # بررسی معتبر بودن category_id
        category = Category.query.get(category_id)
        if not category:
            # اگر دسته‌بندی معتبر نیست، از دسته‌بندی پیش‌فرض استفاده کن
            default_category = Category.query.filter_by(name='عمومی').first()
            if not default_category:
                default_category = Category(
                    name='عمومی',
                    description='دسته‌بندی پیش‌فرض',
                    order=0,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(default_category)
                db.session.flush()
            category_id = default_category.id
    
    if item_id:
        item = MenuItem.query.get(item_id)
        if not item:
            return jsonify({'status': 'error', 'message': 'آیتم یافت نشد'}), 404
        item.name = name
        item.price = price
        item.stock = stock
        item.category_id = category_id
        # اگر آیتم ویرایش می‌شود، آن را فعال می‌کنیم (مگر اینکه صراحتاً غیرفعال شده باشد)
        # چون در صفحه مدیریت منو فقط آیتم‌های فعال نمایش داده می‌شوند
        item.is_active = True
    else:
        item = MenuItem(name=name, price=price, stock=stock, is_active=True, category_id=category_id)
        db.session.add(item)
    
    db.session.commit()
    
    # Return updated item data
    return jsonify({
        'status': 'success',
        'item': {
            'id': item.id,
            'name': item.name,
            'price': item.price,
            'stock': item.stock
        }
    })



@menu_bp.route('/menu/item/<int:item_id>/materials', methods=['GET'])
@login_required
def get_menu_item_materials(item_id):
    item = MenuItem.query.get_or_404(item_id)
    materials = []
    for material in item.materials:
        materials.append({
            'id': material.id,
            'name': material.name,
            'quantity': material.quantity,
            'unit': material.unit,
            'unit_display': normalize_unit(material.unit),
            'raw_material_id': material.raw_material_id,
            'raw_material_name': material.raw_material.name if material.raw_material else None,
            'raw_material_unit_display': normalize_unit(material.raw_material.default_unit) if material.raw_material else None,
            'latest_unit_price': material.latest_unit_price,
            'estimated_cost': material.estimated_cost
        })
    raw_materials = RawMaterial.query.order_by(RawMaterial.name.asc()).all()
    raw_material_options = [
        {
            'id': rm.id,
            'name': rm.name,
            'default_unit': rm.default_unit,
            'default_unit_display': normalize_unit(rm.default_unit),
            'latest_unit_price': rm.latest_unit_price
        } for rm in raw_materials
    ]
    return jsonify({'status': 'success', 'materials': materials, 'units': MATERIAL_UNITS, 'raw_materials': raw_material_options})


@menu_bp.route('/menu/item/<int:item_id>/materials', methods=['POST'])
@login_required
def create_menu_item_material(item_id):
    item = MenuItem.query.get_or_404(item_id)
    data = request.get_json() or {}
    quantity = (data.get('quantity') or '').strip()
    raw_material_id = data.get('raw_material_id')

    if not raw_material_id:
        return jsonify({'status': 'error', 'message': 'انتخاب ماده اولیه الزامی است.'}), 400

    raw_material = RawMaterial.query.get(raw_material_id)
    if not raw_material:
        return jsonify({'status': 'error', 'message': 'ماده اولیه انتخاب شده یافت نشد.'}), 404

    name = raw_material.name

    unit = normalize_unit(data.get('unit') or raw_material.default_unit or MATERIAL_UNITS[0])

    if unit not in MATERIAL_UNITS:
        unit = MATERIAL_UNITS[0]

    if not quantity:
        return jsonify({'status': 'error', 'message': 'مقدار متریال الزامی است.'}), 400

    material = MenuItemMaterial(
        menu_item=item,
        name=name,
        quantity=quantity,
        unit=unit,
        raw_material=raw_material
    )
    db.session.add(material)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'material': {
            'id': material.id,
            'name': material.name,
            'quantity': material.quantity,
            'unit': material.unit,
            'unit_display': normalize_unit(material.unit),
            'raw_material_id': material.raw_material_id,
            'raw_material_name': material.raw_material.name if material.raw_material else None,
            'raw_material_unit_display': normalize_unit(material.raw_material.default_unit) if material.raw_material else None,
            'latest_unit_price': material.latest_unit_price,
            'estimated_cost': material.estimated_cost
        }
    })


@menu_bp.route('/menu/item/<int:item_id>/materials/<int:material_id>', methods=['DELETE'])
@login_required
def delete_menu_item_material(item_id, material_id):
    material = MenuItemMaterial.query.filter_by(id=material_id, menu_item_id=item_id).first()
    if not material:
        abort(404)

    db.session.delete(material)
    db.session.commit()
    return jsonify({'status': 'success'})


@menu_bp.route('/menu/category/add', methods=['POST'])
@login_required
def add_category():
    """اضافه کردن دسته‌بندی جدید"""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    order = int(data.get('order') or 0)
    
    if not name:
        return jsonify({'status': 'error', 'message': 'نام دسته‌بندی الزامی است'}), 400
    
    # بررسی تکراری نبودن نام
    existing = Category.query.filter_by(name=name).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'دسته‌بندی با این نام قبلاً وجود دارد'}), 400
    
    category = Category(
        name=name,
        description=description,
        order=order,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'category': {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'order': category.order,
            'is_active': category.is_active
        }
    })

@menu_bp.route('/menu/category/<int:category_id>/edit', methods=['POST'])
@login_required
def edit_category(category_id):
    """ویرایش دسته‌بندی"""
    category = Category.query.get_or_404(category_id)
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    order = int(data.get('order') or category.order)
    
    if not name:
        return jsonify({'status': 'error', 'message': 'نام دسته‌بندی الزامی است'}), 400
    
    # بررسی تکراری نبودن نام (به جز خودش)
    existing = Category.query.filter(Category.name == name, Category.id != category_id).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'دسته‌بندی با این نام قبلاً وجود دارد'}), 400
    
    category.name = name
    category.description = description
    category.order = order
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'category': {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'order': category.order,
            'is_active': category.is_active
        }
    })

@menu_bp.route('/menu/category/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """حذف دسته‌بندی"""
    category = Category.query.get_or_404(category_id)
    
    # بررسی اینکه آیا آیتمی در این دسته‌بندی وجود دارد (فعال و غیرفعال)
    all_items_count = MenuItem.query.filter_by(category_id=category_id).count()
    active_items_count = MenuItem.query.filter_by(category_id=category_id, is_active=True).count()
    
    if all_items_count > 0:
        # اگر آیتمی وجود دارد (فعال یا غیرفعال)، فقط غیرفعال می‌کنیم
        # چون category_id در MenuItem به صورت NOT NULL تعریف شده، نمی‌توانیم دسته‌بندی را حذف کنیم
        category.is_active = False
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'دسته‌بندی غیرفعال شد ({active_items_count} آیتم فعال و {all_items_count - active_items_count} آیتم غیرفعال در این دسته‌بندی وجود دارد)',
            'deactivated': True
        })
    else:
        # اگر هیچ آیتمی وجود ندارد، می‌توانیم حذف کنیم
        try:
            db.session.delete(category)
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'دسته‌بندی با موفقیت حذف شد',
                'deactivated': False
            })
        except Exception as e:
            db.session.rollback()
            # اگر خطایی رخ داد، فقط غیرفعال می‌کنیم
            category.is_active = False
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': f'دسته‌بندی غیرفعال شد (به دلیل وجود محدودیت‌های دیتابیس، حذف امکان‌پذیر نبود)',
                'deactivated': True
            })

@menu_bp.route('/menu/category/list', methods=['GET'])
@login_required
def list_categories():
    """لیست تمام دسته‌بندی‌ها"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.order, Category.name).all()
    categories_data = []
    for cat in categories:
        items_count = MenuItem.query.filter_by(category_id=cat.id, is_active=True).count()
        categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'order': cat.order,
            'items_count': items_count
        })
    return jsonify({'status': 'success', 'categories': categories_data})

@menu_bp.route('/menu/remove-duplicates', methods=['POST'])
@login_required
def remove_duplicate_menu_items():
    """حذف آیتم‌های تکراری و نگه داشتن آیتم با بالاترین قیمت"""
    from collections import defaultdict
    
    # دریافت همه آیتم‌های منو
    all_items = MenuItem.query.all()
    
    # گروه‌بندی بر اساس نام
    items_by_name = defaultdict(list)
    for item in all_items:
        items_by_name[item.name].append(item)
    
    deleted_count = 0
    deactivated_count = 0
    groups_processed = 0
    
    # پردازش هر گروه
    for name, items in items_by_name.items():
        if len(items) > 1:  # فقط گروه‌هایی که تکراری هستند
            groups_processed += 1
            
            # پیدا کردن آیتم با بالاترین قیمت
            items_sorted = sorted(items, key=lambda x: x.price, reverse=True)
            keep_item = items_sorted[0]  # آیتم با بالاترین قیمت
            
            # حذف یا غیرفعال کردن بقیه
            for item in items_sorted[1:]:  # از دومی به بعد
                # بررسی اینکه آیا در سفارش استفاده شده یا نه
                if item.order_items and len(item.order_items) > 0:
                    # اگر استفاده شده، فقط غیرفعال می‌کنیم
                    item.is_active = False
                    deactivated_count += 1
                else:
                    # اگر استفاده نشده، حذف می‌کنیم
                    db.session.delete(item)
                    deleted_count += 1
    
    db.session.commit()
    
    total_removed = deleted_count + deactivated_count
    message = f'{groups_processed} گروه تکراری پیدا شد. {total_removed} آیتم حذف یا غیرفعال شد: {deleted_count} مورد حذف شد و {deactivated_count} مورد غیرفعال شد.'
    
    return jsonify({
        'status': 'success',
        'message': message,
        'groups_processed': groups_processed,
        'deleted_count': deleted_count,
        'deactivated_count': deactivated_count,
        'total_removed': total_removed
    })
