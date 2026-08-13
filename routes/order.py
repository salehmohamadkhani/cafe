from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models.models import (
    db,
    MenuItem,
    Order,
    OrderItem,
    Customer,
    Settings,
    Table,
    TableItem,
    find_or_create_customer,
    generate_invoice_number,
    calculate_order_amount,
    sync_order_item_material_usage,
    record_order_material_usage,
    RawMaterialUsage,
)
from sqlalchemy import func, or_
from datetime import datetime
import pytz
import sys

# Import Windows-specific modules only on Windows
if sys.platform == 'win32':
    try:
        import win32print
        import win32ui
    except ImportError:
        win32print = None
        win32ui = None
else:
    win32print = None
    win32ui = None

order_bp = Blueprint('order', __name__)

# --- لیست سفارش‌ها با فیلتر و جستجو ---
@order_bp.route('/orders')
@login_required
def orders_list():
    q = request.args.get('q')
    status = request.args.get('status')
    customer_id = request.args.get('customer_id', type=int)
    orders_query = Order.query
    if status:
        orders_query = orders_query.filter_by(status=status)
    if customer_id:
        orders_query = orders_query.filter_by(customer_id=customer_id)
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
    orders = orders_query.order_by(Order.created_at.desc()).all()
    return render_template('orders/orders_list.html', orders=orders, q=q, status=status)

# --- ثبت سفارش جدید (فرم) ---
@order_bp.route('/order/new')
@login_required # Added login_required as it's likely needed for creating orders
def new_order_form():
    menu_items = MenuItem.query.filter_by(is_active=True).order_by(MenuItem.name).all()
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0

    return render_template('orders/create_order.html', menu_items=menu_items, tax_percent=tax_percent)

# --- ثبت سفارش جدید (ذخیره) ---
@order_bp.route('/order', methods=['POST'])
@login_required # Added login_required
def create_order():
    customer_name = request.form.get('customer_name')
    customer_phone = request.form.get('customer_phone')
    
    # Add debug print statements
    print("📥 سفارش جدید ثبت شد برای:", customer_name, customer_phone)
    print("آیتم‌ها:", request.form.getlist('item'))
    print("تعداد‌ها:", request.form.getlist('quantity'))
    
    discount = int(request.form.get('discount', 0))
    order_type = request.form.get('type', 'حضوری')
    order_status = request.form.get('status', 'پرداخت نشده')
    items = request.form.getlist('item')
    quantities = request.form.getlist('quantity')

    if not items or not quantities or len(items) != len(quantities):
        flash('لطفاً حداقل یک آیتم برای سفارش انتخاب کنید.', 'danger')
        return redirect(url_for('order.new_order_form')) # Redirect back to form on error

    customer = find_or_create_customer(customer_name, customer_phone)
    invoice_identifiers = generate_invoice_number()
    settings = Settings.query.first() # Fetch settings again
    tax_percent = settings.tax_percent if settings else 9.0

    order_items_data = []
    for item_id, qty in zip(items, quantities):
        menu_item = MenuItem.query.get(int(item_id))
        qty = int(qty)
        if menu_item and qty > 0: # Ensure item exists and quantity is positive
            # کاهش موجودی آیتم
            if menu_item.stock is not None:
                menu_item.stock = max(0, menu_item.stock - qty)
            
            order_items_data.append({
                'menu_item_id': menu_item.id,
                'quantity': qty,
                'unit_price': int(menu_item.price),
                'total_price': int(menu_item.price * qty)
            })
        else:
            flash(f'آیتم با شناسه {item_id} نامعتبر است یا تعداد آن صفر است.', 'warning')
            # Optionally, you might want to break or handle this more strictly

    if not order_items_data: # Check if any valid items were added
        flash('هیچ آیتم معتبری برای ثبت سفارش وجود ندارد.', 'danger')
        return redirect(url_for('order.new_order_form'))

    total, tax, final = calculate_order_amount(order_items_data, discount, tax_percent)

    iran_tz = pytz.timezone('Asia/Tehran')
    created_at = datetime.now(iran_tz)

    order = Order(
        invoice_number=invoice_identifiers.unique_number,
        daily_sequence=invoice_identifiers.daily_sequence,
        invoice_uid=invoice_identifiers.invoice_uid,
        customer_id=customer.id,
        total_amount=total,
        discount=discount,
        tax_amount=tax,
        final_amount=final,
        created_at=created_at,  # زمان با تایم‌زون ایران
        status=order_status,    # اگر هست
        type=order_type,        # اگر هست
        user_id=current_user.id
    )

    db.session.add(order)
    db.session.flush()  # تا بتونیم id سفارش رو بگیریم

    order_items = []
    for oi in order_items_data:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=oi['menu_item_id'],
            quantity=oi['quantity'],
            unit_price=oi['unit_price'],
            total_price=oi['total_price']
        )
        db.session.add(order_item)
        order_items.append(order_item)

    db.session.flush()
    record_order_material_usage(order)

    db.session.commit()
    print_invoice(order)
    flash(f'سفارش با شماره فاکتور روزانه {order.daily_sequence} (شناسه {order.invoice_uid}) با موفقیت ثبت شد!', 'success')
    return jsonify(success=True, order_id=order.id, daily_invoice_number=order.daily_sequence, invoice_uid=order.invoice_uid)
# --- نمایش جزئیات سفارش ---
@order_bp.route('/order/<int:order_id>') # Added route for detail page
@login_required # Added login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    menu_items = MenuItem.query.filter_by(is_active=True).order_by(MenuItem.name).all()
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    return render_template('orders/order_detail.html', order=order, menu_items=menu_items, tax_percent=tax_percent)

# --- پرداخت سفارش ---
@order_bp.route('/order/<int:order_id>/pay', methods=['POST'])
@login_required
def pay_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'پرداخت شده':
        flash('این سفارش قبلاً پرداخت شده است.', 'warning')
        return redirect(url_for('order.order_detail', order_id=order.id))
    order.status = 'پرداخت شده'
    order.paid_at = datetime.utcnow()
    order.payment_method = request.form.get('payment_method', 'کارتخوان')
    db.session.commit()
    flash('سفارش با موفقیت پرداخت شد.', 'success')
    return redirect(url_for('order.order_detail', order_id=order.id))

# --- حذف سفارش ---
@order_bp.route('/order/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    RawMaterialUsage.query.filter_by(order_id=order.id).delete(synchronize_session=False)
    for item in order.order_items:
        item.is_deleted = True
        item.removal_reason = item.removal_reason or 'لغو کامل سفارش'
    order.status = 'لغو شده'
    order.total_amount = 0
    order.tax_amount = 0
    order.final_amount = 0
    db.session.commit()
    flash('سفارش لغو شد؛ سابقه آن برای حسابرسی نگهداری و موجودی آزاد شد.', 'success')
    return redirect(url_for('order.orders_list'))

# --- ویرایش سفارش (redirect به جزئیات) ---
@order_bp.route('/order/<int:order_id>/edit', methods=['GET'])
@login_required
def edit_order(order_id):
    """redirect به صفحه جزئیات سفارش برای ویرایش"""
    return redirect(url_for('order.order_detail', order_id=order_id))

# --- به‌روزرسانی آیتم سفارش (API) ---
@order_bp.route('/order/item/<int:item_id>/update', methods=['POST'])
@login_required
def update_order_item(item_id):
    """به‌روزرسانی تعداد یا آیتم یک آیتم سفارش"""
    order_item = OrderItem.query.get_or_404(item_id)
    order = order_item.order
    
    data = request.get_json()
    new_menu_item_id = data.get('menu_item_id')
    new_quantity = data.get('quantity')
    
    if new_menu_item_id:
        menu_item = MenuItem.query.get_or_404(int(new_menu_item_id))
        order_item.menu_item_id = menu_item.id
        order_item.unit_price = int(menu_item.price)
    
    if new_quantity:
        qty = int(new_quantity)
        if qty <= 0:
            return jsonify({'success': False, 'message': 'تعداد باید بیشتر از صفر باشد.'}), 400
        order_item.quantity = qty
        order_item.total_price = order_item.unit_price * qty

    db.session.flush()
    sync_order_item_material_usage(order_item)
    
    # محاسبه مجدد مجموع سفارش
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    # فقط آیتم‌های حذف نشده را در نظر بگیر
    order_items_data = [{
        'menu_item_id': item.menu_item_id,
        'quantity': item.quantity,
        'unit_price': item.unit_price,
        'total_price': item.total_price
    } for item in order.order_items if not item.is_deleted]
    
    total, tax, final = calculate_order_amount(order_items_data, order.discount, tax_percent)
    order.total_amount = total
    order.tax_amount = tax
    order.final_amount = final
    
    db.session.commit()
    return jsonify({
        'success': True,
        'order_item': {
            'id': order_item.id,
            'name': order_item.menu_item.name,
            'quantity': order_item.quantity,
            'unit_price': order_item.unit_price,
            'total_price': order_item.total_price
        },
        'order': {
            'total_amount': order.total_amount,
            'tax_amount': order.tax_amount,
            'final_amount': order.final_amount
        }
    })

# --- به‌روزرسانی اطلاعات سفارش (API) ---
@order_bp.route('/order/<int:order_id>/update', methods=['POST'])
@login_required
def update_order(order_id):
    """به‌روزرسانی تخفیف، وضعیت، نوع سفارش"""
    order = Order.query.get_or_404(order_id)
    data = request.get_json()
    
    if 'discount' in data:
        order.discount = int(data['discount'])
    if 'status' in data:
        order.status = data['status']
    if 'type' in data:
        order.type = data['type']
    
    # محاسبه مجدد
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    order_items_data = [{
        'menu_item_id': item.menu_item_id,
        'quantity': item.quantity,
        'unit_price': item.unit_price,
        'total_price': item.total_price
    } for item in order.order_items if not item.is_deleted]
    
    total, tax, final = calculate_order_amount(order_items_data, order.discount, tax_percent)
    order.total_amount = total
    order.tax_amount = tax
    order.final_amount = final
    
    db.session.commit()
    return jsonify({
        'success': True,
        'order': {
            'discount': order.discount,
            'status': order.status,
            'type': order.type,
            'total_amount': order.total_amount,
            'tax_amount': order.tax_amount,
            'final_amount': order.final_amount
        }
    })

# --- ادغام آیتم‌های تکراری در سفارش‌ها ---
@order_bp.route('/orders/merge-duplicates', methods=['POST'])
@login_required
def merge_duplicate_order_items():
    """ادغام آیتم‌های تکراری در همه سفارش‌ها (با همان menu_item_id و unit_price)"""
    from collections import defaultdict
    
    all_orders = Order.query.all()
    orders_processed = 0
    total_merged = 0
    
    for order in all_orders:
        # گروه‌بندی آیتم‌ها بر اساس menu_item_id و unit_price (فقط آیتم‌های حذف نشده)
        items_by_key = defaultdict(list)
        for item in order.order_items:
            if not item.is_deleted:  # فقط آیتم‌های حذف نشده
                key = (item.menu_item_id, item.unit_price)
                items_by_key[key].append(item)
        
        order_merged = False
        for key, items in items_by_key.items():
            if len(items) > 1:  # اگر تکراری وجود دارد
                order_merged = True
                # آیتم اول را نگه می‌داریم و بقیه را با آن ادغام می‌کنیم
                keep_item = items[0]
                total_quantity = sum(item.quantity for item in items)
                
                # به‌روزرسانی آیتم نگه‌داشته شده
                keep_item.quantity = total_quantity
                keep_item.total_price = keep_item.unit_price * total_quantity
                sync_order_item_material_usage(keep_item)
                
                # حذف بقیه آیتم‌ها
                for item in items[1:]:
                    db.session.delete(item)
                    total_merged += 1
        
        if order_merged:
            orders_processed += 1
            # محاسبه مجدد مجموع سفارش
            settings = Settings.query.first()
            tax_percent = settings.tax_percent if settings else 9.0
            # فقط آیتم‌های حذف نشده را در نظر بگیر
            order_items_data = [{
                'menu_item_id': item.menu_item_id,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price
            } for item in order.order_items if not item.is_deleted]
            
            total, tax, final = calculate_order_amount(order_items_data, order.discount, tax_percent)
            order.total_amount = total
            order.tax_amount = tax
            order.final_amount = final
    
    db.session.commit()
    
    message = f'{orders_processed} سفارش پردازش شد. {total_merged} آیتم تکراری ادغام شد.'
    
    return jsonify({
        'success': True,
        'message': message,
        'orders_processed': orders_processed,
        'items_merged': total_merged
    })

# --- افزودن آیتم به سفارش (AJAX) ---
# Note: This route seems redundant with the edit_order route's functionality
# but kept as per original code structure. It might be intended for a different UI flow.
@order_bp.route('/order/<int:order_id>/add_item', methods=['POST'])
@login_required
def add_order_item(order_id):
    order = Order.query.get_or_404(order_id)
    menu_item_id = int(request.form['menu_item_id'])
    quantity = int(request.form['quantity'])
    menu_item = MenuItem.query.get_or_404(menu_item_id)

    if quantity <= 0:
        flash('تعداد آیتم باید بیشتر از صفر باشد.', 'warning')
        return redirect(url_for('order.order_detail', order_id=order.id))

    order_item = OrderItem(
        order_id=order.id,
        menu_item_id=menu_item.id,
        quantity=quantity,
        unit_price=int(menu_item.price),
        total_price=int(menu_item.price * quantity)
    )
    db.session.add(order_item)
    db.session.flush()
    sync_order_item_material_usage(order_item)
    
    # کم کردن موجودی آیتم منو
    if menu_item.stock is not None:
        menu_item.stock = max(menu_item.stock - quantity, 0)
        db.session.add(menu_item)
    
    # Recalculate order totals after adding item
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    # فقط آیتم‌های حذف نشده را در نظر بگیر
    order_items_data = [{
        'menu_item_id': item.menu_item_id,
        'quantity': item.quantity,
        'unit_price': item.unit_price,
        'total_price': item.total_price
    } for item in order.order_items if not item.is_deleted] # Get existing items + the new one added to session
    total, tax, final = calculate_order_amount(order_items_data, order.discount, tax_percent)
    order.total_amount = total
    order.tax_amount = tax
    order.final_amount = final

    db.session.commit()
    flash('آیتم به سفارش اضافه شد.', 'success')
    return redirect(url_for('order.order_detail', order_id=order.id))

# --- تابع کمکی برای بررسی اولین ثبت سفارش روز ---
def is_first_order_of_day(order_id):
    """بررسی می‌کند که آیا سفارش اولین ثبت روز است یا نه"""
    if not order_id:
        return False
    order = Order.query.get(order_id)
    if not order:
        return False
    # اولین سفارش روز daily_sequence = 100 دارد
    return order.daily_sequence == 100

# --- حذف آیتم از سفارش (AJAX) ---
@order_bp.route('/order/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_order_item(item_id):
    order_item = OrderItem.query.get_or_404(item_id)
    order_id = order_item.order_id
    order = order_item.order
    associated_table = order.table

    # اگر سفارش هنوز تسویه نشده باشد، باید دلیل حذف را بپرسیم
    if order.status != 'پرداخت شده':
        # باید دلیل حذف را از درخواست بگیریم
        removal_reason = request.form.get('removal_reason', '').strip()
        if not removal_reason:
            flash('برای حذف آیتم از سفارش ثبت شده، باید دلیل حذف را وارد کنید', 'warning')
            return redirect(url_for('order.order_detail', order_id=order_id))
        
        # ذخیره دلیل حذف و علامت‌گذاری به عنوان حذف شده
        order_item.removal_reason = removal_reason
        order_item.is_deleted = True
    else:
        # اگر تسویه شده باشد، فقط علامت‌گذاری می‌کنیم
        order_item.is_deleted = True

    db.session.flush()
    sync_order_item_material_usage(order_item)

    # فقط آیتم‌های حذف نشده را در نظر بگیر
    remaining_items = [item for item in order.order_items if not item.is_deleted]

    if not remaining_items:
        if associated_table:
            TableItem.query.filter_by(table_id=associated_table.id).delete()
            associated_table.status = 'خالی'
            associated_table.customer_name = None
            associated_table.customer_phone = None
            associated_table.order_id = None
            associated_table.total_amount = 0
            associated_table.discount = 0
            associated_table.tax_amount = 0
            associated_table.final_amount = 0
            associated_table.started_at = None
        RawMaterialUsage.query.filter_by(order_id=order.id).delete(synchronize_session=False)
        order.status = 'لغو شده'
        order.total_amount = 0
        order.tax_amount = 0
        order.final_amount = 0
        db.session.commit()
        flash('تمام آیتم‌ها لغو شد؛ میز آزاد و موجودی مواد برگردانده شد.', 'success')
        return redirect(url_for('order.orders_list'))

    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    # فقط آیتم‌های حذف نشده را در نظر بگیر
    order_items_data = [{
        'menu_item_id': item.menu_item_id,
        'quantity': item.quantity,
        'unit_price': item.unit_price,
        'total_price': item.total_price
    } for item in remaining_items if not item.is_deleted]

    total, tax, final = calculate_order_amount(order_items_data, order.discount, tax_percent)
    order.total_amount = total
    order.tax_amount = tax
    order.final_amount = final

    db.session.commit() # Commit updated order totals

    flash('آیتم از سفارش حذف شد.', 'success')
    return redirect(url_for('order.order_detail', order_id=order_id))

# --- جستجوی سریع مشتری (AJAX) ---
@order_bp.route('/customer/search')
@login_required
def search_customer():
    q = request.args.get('q')
    if not q:
        return jsonify([])
    customers = Customer.query.filter(
        (Customer.name.ilike(f'%{q}%')) | (Customer.phone.ilike(f'%{q}%'))
    ).all()
    results = []
    for c in customers:
        # بررسی اینکه آیا مشتری سفارش قبلی دارد یا نه
        has_orders = Order.query.filter_by(customer_id=c.id).count() > 0
        results.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'has_orders': has_orders,
            'birth_date': c.birth_date.isoformat() if c.birth_date else None
        })
    return jsonify(results)

# --- ثبت مشتری جدید ---
@order_bp.route('/customer/register', methods=['POST'])
@login_required
def register_customer():
    """ثبت مشتری جدید در دیتابیس"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        birth_date_str = data.get('birth_date')
        
        if not name:
            return jsonify({'success': False, 'message': 'نام مشتری الزامی است'}), 400
        
        # بررسی اینکه آیا مشتری با این نام یا شماره تماس وجود دارد
        existing_customer = None
        if phone:
            existing_customer = Customer.query.filter_by(phone=phone).first()
        if not existing_customer and name:
            existing_customer = Customer.query.filter_by(name=name).first()
        
        if existing_customer:
            return jsonify({
                'success': True,
                'message': 'مشتری با این اطلاعات قبلاً ثبت شده است',
                'customer': {
                    'id': existing_customer.id,
                    'name': existing_customer.name,
                    'phone': existing_customer.phone,
                    'birth_date': existing_customer.birth_date.isoformat() if existing_customer.birth_date else None
                }
            })
        
        # ایجاد مشتری جدید
        birth_date = None
        if birth_date_str:
            try:
                from datetime import datetime as dt
                birth_date = dt.strptime(birth_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        
        customer = Customer(
            name=name,
            phone=phone if phone else None,
            birth_date=birth_date,
            created_at=datetime.now(pytz.timezone('Asia/Tehran'))
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'مشتری با موفقیت ثبت شد',
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'birth_date': customer.birth_date.isoformat() if customer.birth_date else None
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"خطا در ثبت مشتری: {e}")
        return jsonify({'success': False, 'message': f'خطا در ثبت مشتری: {str(e)}'}), 500

# --- نمایش سفارش‌های جاری (پرداخت نشده/بیرون‌بر) برای داشبورد ---
@order_bp.route('/orders/current')
@login_required
def current_orders():
    orders = Order.query.filter(Order.status.in_(['پرداخت نشده', 'بیرون‌بر'])).order_by(Order.created_at.desc()).all()
    return render_template('orders/current_orders.html', orders=orders)

# --- API سفارش‌ها (برای اپلیکیشن موبایل یا داشبورد JS) ---
@order_bp.route('/api/orders')
@login_required
def api_orders():
    orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    result = []
    for o in orders:
        result.append({
            'id': o.id,
            'invoice_number': o.invoice_number,
            'daily_invoice_number': o.daily_sequence,
            'invoice_uid': o.invoice_uid,
            'customer': o.customer.name,
            'phone': o.customer.phone,
            'status': o.status,
            'type': o.type,
            'final_amount': o.final_amount,
            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
            'items': [
                {
                    'name': oi.menu_item.name,
                    'quantity': oi.quantity,
                    'unit_price': oi.unit_price,
                    'total_price': oi.total_price
                } for oi in o.order_items
            ]
        })
    return jsonify(result)

# --- خطای پیدا نشدن ---
@order_bp.app_errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

# --- خطای سرور ---
@order_bp.app_errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

@order_bp.route('/orders/create', methods=['POST'])
@login_required
def create_order_api():
    try:
        data = request.get_json()
        customer_name = data.get('customer_name')
        customer_phone = data.get('customer_phone')
        discount = int(data.get('discount', 0))
        tax_percent = int(data.get('tax_percent', 9))
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'message': 'هیچ آیتمی انتخاب نشده است.'}), 400
            
        customer = find_or_create_customer(customer_name, customer_phone)
        invoice_identifiers = generate_invoice_number()
        
        order_items_data = []
        print("📦 Items received from client:", items)
        for item in items:
            print("🧪 Processing item:", item)
            item_id = int(item.get('id'))
            qty = int(item.get('quantity'))
            menu_item = MenuItem.query.filter_by(id=item_id, is_active=True).first()
            if not menu_item or qty <= 0:
                return jsonify({'success': False, 'message': f'آیتم نامعتبر: {item_id}'}), 400
                
            # کم کردن موجودی همان لحظه
            menu_item.stock = max(menu_item.stock - qty, 0)
                
            order_items_data.append({
                'menu_item_id': item_id,
                'quantity': qty,
                'unit_price': int(menu_item.price),
                'total_price': int(menu_item.price * qty)
            })
            
        total, tax, final = calculate_order_amount(order_items_data, discount, tax_percent)
        
        order = Order(
            invoice_number=invoice_identifiers.unique_number,
            daily_sequence=invoice_identifiers.daily_sequence,
            invoice_uid=invoice_identifiers.invoice_uid,
            customer_id=customer.id,
            total_amount=total,
            discount=discount,
            tax_amount=tax,
            final_amount=final,
            status='پرداخت نشده',
            type='حضوری',
            user_id=current_user.id
        )
        
        db.session.add(order)
        db.session.flush()
        
        order_items = []
        for oi in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=oi['menu_item_id'],
                quantity=oi['quantity'],
                unit_price=oi['unit_price'],
                total_price=oi['total_price']
            )
            db.session.add(order_item)
            order_items.append(order_item)

            
        db.session.commit()
        
        # Get updated stock information
        updated_stocks = [{'id': MenuItem.query.get(oi['menu_item_id']).id, 
                          'stock': MenuItem.query.get(oi['menu_item_id']).stock} 
                         for oi in order_items_data]
        
        return jsonify({
            'success': True,
            'order_id': order.id,
            'updatedStocks': updated_stocks,
            'daily_invoice_number': order.daily_sequence,
            'invoice_uid': order.invoice_uid
        })
        
    except Exception as e:
        print("خطای ثبت سفارش:", e)
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطای داخلی سرور'}), 500

@order_bp.route('/api/menu_stock')
@login_required
def api_menu_stock():
    from services.inventory_service import menu_stock_map
    items = MenuItem.query.filter_by(is_active=True).all()
    stocks = menu_stock_map(items)
    return jsonify([
        {'id': item.id, 'stock': stocks[item.id]}
        for item in items
    ])

from flask import render_template
from flask_login import login_required
from models.models import Order

@order_bp.route('/orders/<int:order_id>/invoice')
@login_required
def print_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    print(f"🧾 Printing invoice for Order ID: {order_id} | Total: {order.final_amount}")
    return render_template('invoice.html', order=order)

@order_bp.route('/orders/<int:order_id>/invoice/text')
@login_required
def get_invoice_text(order_id):
    """دریافت محتوای فاکتور به صورت متن برای کپی"""
    from models.models import Settings
    from utils.helpers import to_jalali
    import jdatetime
    
    order = Order.query.get_or_404(order_id)
    settings = Settings.query.first()
    
    # ساخت متن فاکتور
    invoice_text = ""
    invoice_text += f"{settings.cafe_name if settings else 'Madeline'}\n"
    if settings and settings.address:
        invoice_text += f"{settings.address}\n"
    if settings and settings.phone:
        invoice_text += f"تلفن: {settings.phone}\n"
    invoice_text += "\n"
    invoice_text += f"شماره فاکتور روزانه: {order.daily_sequence or '-'}\n"
    invoice_text += f"شناسه یکتا: {order.invoice_uid or order.invoice_number}\n"
    
    # تبدیل تاریخ به شمسی
    if order.created_at:
        try:
            date_str = to_jalali(order.created_at)
        except:
            date_str = order.created_at.strftime('%Y-%m-%d %H:%M')
    else:
        date_str = 'نامشخص'
    invoice_text += f"تاریخ: {date_str}\n"
    
    if order.customer and order.customer.name != "عمومی":
        invoice_text += f"مشتری: {order.customer.name}\n"
    invoice_text += "\n"
    invoice_text += "=" * 30 + "\n"
    invoice_text += "شرح | تعداد | قیمت واحد | مبلغ کل\n"
    invoice_text += "=" * 30 + "\n"
    
    # فقط آیتم‌های حذف نشده را در فاکتور نمایش بده
    for item in order.order_items:
        if not item.is_deleted:
            invoice_text += f"{item.menu_item.name} | {item.quantity} | {item.unit_price:,} | {item.total_price:,}\n"
    
    invoice_text += "=" * 30 + "\n"
    invoice_text += f"جمع کل موارد: {order.total_amount:,}\n"
    
    if order.discount > 0:
        invoice_text += f"تخفیف: {order.discount:,}\n"
    
    tax_percent = settings.tax_percent if settings else 9
    invoice_text += f"مالیات ({tax_percent}%): {order.tax_amount:,}\n"
    invoice_text += f"مبلغ نهایی قابل پرداخت: {order.final_amount:,}\n"
    invoice_text += "\n"
    invoice_text += "شماره کارت: 6104338745684122\n"
    invoice_text += "\n"
    invoice_text += "از خرید شما متشکریم!\n"
    
    return jsonify({
        'success': True,
        'text': invoice_text
    })



def print_invoice(order):
    invoice_text = f"""فاکتور روزانه: {order.daily_sequence or '-'}
شناسه یکتا: {order.invoice_uid or order.invoice_number}
تاریخ: {order.created_at.strftime('%Y-%m-%d %H:%M')}
مشتری: {order.customer.name}
-------------------------------
"""
    # فقط آیتم‌های حذف نشده را در فاکتور نمایش بده
    for item in order.order_items:
        if not item.is_deleted:
            invoice_text += f"{item.menu_item.name} x{item.quantity} = {item.total_price}\n"
    invoice_text += "-------------------------------\n"
    invoice_text += f"جمع کل: {order.total_amount}\n"
    invoice_text += f"تخفیف: {order.discount}\n"
    invoice_text += f"مالیات: {order.tax_amount}\n"
    invoice_text += f"مبلغ نهایی: {order.final_amount}\n"
    invoice_text += "\nبا تشکر 🌸"

    # Print only on Windows
    if sys.platform == 'win32' and win32print:
        try:
            printer_name = win32print.GetDefaultPrinter()
            hprinter = win32print.OpenPrinter(printer_name)
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            hdc.StartDoc("Cafe Invoice")
            hdc.StartPage()
            hdc.TextOut(100, 100, invoice_text)
            hdc.EndPage()
            hdc.EndDoc()
            win32print.ClosePrinter(hprinter)
        except Exception as e:
            print(f"خطا در چاپ: {e}")
