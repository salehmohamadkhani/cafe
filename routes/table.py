from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from models.models import (
    db,
    Table,
    TableItem,
    MenuItem,
    Order,
    OrderItem,
    Customer,
    Settings,
    find_or_create_customer,
    generate_invoice_number,
    calculate_order_amount,
    sync_order_item_material_usage
)
from datetime import datetime
import pytz

table_bp = Blueprint('table', __name__, url_prefix='/table')

# --- دریافت اطلاعات میز ---
@table_bp.route('/<int:table_id>', methods=['GET'])
@login_required
def get_table(table_id):
    table = Table.query.get_or_404(table_id)
    
    items_data = []
    order_status = None
    
    # اگر سفارش ثبت شده باشد، OrderItem ها را برگردان
    order = None
    if table.order_id:
        order = Order.query.get(table.order_id)
        if order:
            order_status = order.status
            # فقط آیتم‌های حذف نشده را برگردان
            order_items = OrderItem.query.filter_by(order_id=order.id, is_deleted=False).all()
            for item in order_items:
                items_data.append({
                    'id': item.id,  # OrderItem.id
                    'menu_item_id': item.menu_item_id,
                    'menu_item_name': item.menu_item.name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'total_price': item.total_price,
                    'is_order_item': True  # نشان می‌دهد که این OrderItem است
                })
    else:
        # اگر سفارش ثبت نشده باشد، TableItem ها را برگردان
        table_items = TableItem.query.filter_by(table_id=table_id).all()
        for item in table_items:
            items_data.append({
                'id': item.id,  # TableItem.id
                'menu_item_id': item.menu_item_id,
                'menu_item_name': item.menu_item.name,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price,
                'is_order_item': False  # نشان می‌دهد که این TableItem است
            })
    
    # اگر سفارش ثبت شده باشد، از order.final_amount استفاده کن، در غیر این صورت از table.final_amount
    final_amount = order.final_amount if order else table.final_amount
    total_amount = order.total_amount if order else table.total_amount
    tax_amount = order.tax_amount if order else table.tax_amount
    discount = order.discount if order else table.discount
    
    return jsonify({
        'id': table.id,
        'number': table.number,
        'status': table.status,
        'customer_name': table.customer_name or '',
        'customer_phone': table.customer_phone or '',
        'total_amount': total_amount,
        'discount': discount,
        'tax_amount': tax_amount,
        'final_amount': final_amount,
        'order_id': table.order_id,
        'order_status': order_status,  # وضعیت سفارش
        'items': items_data
    })

# --- افزودن آیتم به میز ---
@table_bp.route('/<int:table_id>/add_item', methods=['POST'])
@login_required
def add_item_to_table(table_id):
    table = Table.query.get_or_404(table_id)
    data = request.get_json()
    menu_item_id = data.get('menu_item_id')
    quantity = int(data.get('quantity', 1))
    
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    
    # اگر سفارش ثبت شده باشد، باید OrderItem اضافه کنیم
    if table.order_id:
        order = Order.query.get(table.order_id)
        if order:
            # بررسی وجود آیتم در سفارش (فقط آیتم‌های حذف نشده)
            existing_item = OrderItem.query.filter_by(
                order_id=order.id,
                menu_item_id=menu_item_id,
                is_deleted=False
            ).first()
            
            if existing_item:
                existing_item.quantity += quantity
                existing_item.total_price = existing_item.quantity * existing_item.unit_price
            else:
                new_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item_id,
                    quantity=quantity,
                    unit_price=int(menu_item.price),
                    total_price=int(menu_item.price * quantity)
                )
                db.session.add(new_item)
                db.session.flush()
                sync_order_item_material_usage(new_item)
            
            # کم کردن موجودی آیتم منو
            if menu_item.stock is not None:
                menu_item.stock = max(menu_item.stock - quantity, 0)
            
            # به‌روزرسانی مبلغ سفارش
            update_order_totals(order)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'آیتم اضافه شد'})
    
    # اگر سفارش ثبت نشده باشد، TableItem اضافه می‌کنیم
    existing_item = TableItem.query.filter_by(
        table_id=table_id,
        menu_item_id=menu_item_id
    ).first()
    
    if existing_item:
        existing_item.quantity += quantity
        existing_item.total_price = existing_item.quantity * existing_item.unit_price
    else:
        new_item = TableItem(
            table_id=table_id,
            menu_item_id=menu_item_id,
            quantity=quantity,
            unit_price=menu_item.price,
            total_price=menu_item.price * quantity
        )
        db.session.add(new_item)
    
    # به‌روزرسانی وضعیت میز
    if table.status == 'خالی':
        table.status = 'اشغال شده'
        table.started_at = datetime.now(pytz.timezone('Asia/Tehran'))
    
    # محاسبه مبلغ کل
    update_table_totals(table)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'آیتم اضافه شد'})

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

# --- بررسی اولین سفارش روز برای میز ---
@table_bp.route('/<int:table_id>/check_first_order', methods=['GET'])
@login_required
def check_first_order(table_id):
    """بررسی می‌کند که آیا سفارش میز اولین ثبت روز است یا نه"""
    table = Table.query.get_or_404(table_id)
    is_first = False
    if table.order_id:
        is_first = is_first_order_of_day(table.order_id)
    return jsonify({'is_first_order': is_first})

# --- حذف آیتم از میز ---
@table_bp.route('/<int:table_id>/remove_item/<int:item_id>', methods=['DELETE'])
@login_required
def remove_item_from_table(table_id, item_id):
    table = Table.query.get_or_404(table_id)
    
    # اگر سفارش ثبت شده باشد، باید OrderItem را حذف کنیم
    if table.order_id:
        order = Order.query.get(table.order_id)
        if order:
            # پیدا کردن OrderItem با item_id (که در این حالت OrderItem.id است)
            order_item = OrderItem.query.filter_by(
                id=item_id,
                order_id=order.id
            ).first()
            
            if not order_item:
                return jsonify({'success': False, 'message': 'آیتم یافت نشد'}), 404
            
            if order_item:
                # اگر سفارش هنوز تسویه نشده باشد، باید دلیل حذف را بپرسیم
                if order.status != 'پرداخت شده':
                    # باید دلیل حذف را از درخواست بگیریم
                    data = request.get_json() or {}
                    removal_reason = data.get('removal_reason', '').strip()
                    if not removal_reason:
                        return jsonify({
                            'success': False, 
                            'message': 'برای حذف آیتم از سفارش ثبت شده، باید دلیل حذف را وارد کنید',
                            'requires_reason': True
                        }), 400
                    
                    # ذخیره دلیل حذف و علامت‌گذاری به عنوان حذف شده
                    order_item.removal_reason = removal_reason
                    order_item.is_deleted = True
                # به‌روزرسانی مبلغ سفارش
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
                
                # اگر همه آیتم‌ها حذف شده‌اند، سفارش را حذف کن
                remaining_order_items = OrderItem.query.filter_by(order_id=order.id, is_deleted=False).count()
                if remaining_order_items == 0:
                    db.session.delete(order)
                    table.order_id = None
                    table.status = 'خالی'
                    table.customer_name = None
                    table.customer_phone = None
                    table.discount = 0
                    table.total_amount = 0
                    table.tax_amount = 0
                    table.final_amount = 0
                    table.started_at = None
                
                db.session.commit()
                return jsonify({'success': True, 'message': 'آیتم حذف شد'})
    
    # اگر سفارش ثبت نشده، TableItem را حذف می‌کنیم
    table_item = TableItem.query.get(item_id)
    if not table_item:
        return jsonify({'success': False, 'message': 'آیتم یافت نشد'}), 404
    
    if table_item.table_id != table_id:
        return jsonify({'success': False, 'message': 'آیتم متعلق به این میز نیست'}), 400
    
    db.session.delete(table_item)
    update_table_totals(table)
    
    # اگر میز خالی شد
    remaining_items = TableItem.query.filter_by(table_id=table_id).count()
    if remaining_items == 0:
        table.status = 'خالی'
        table.customer_name = None
        table.customer_phone = None
        table.discount = 0  # ریست کردن تخفیف
        # اگر سفارشی وجود دارد، آن را حذف کن
        if table.order_id:
            order = Order.query.get(table.order_id)
            if order:
                # حذف آیتم‌های سفارش
                OrderItem.query.filter_by(order_id=order.id).delete()
                # حذف سفارش
                db.session.delete(order)
            table.order_id = None
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'آیتم حذف شد'})

# --- به‌روزرسانی تعداد آیتم ---
@table_bp.route('/<int:table_id>/update_item/<int:item_id>', methods=['PUT'])
@login_required
def update_item_quantity(table_id, item_id):
    table = Table.query.get_or_404(table_id)
    table_item = TableItem.query.get_or_404(item_id)
    data = request.get_json()
    quantity = int(data.get('quantity', 1))
    
    if quantity <= 0:
        return remove_item_from_table(table_id, item_id)
    
    if table_item.table_id != table_id:
        return jsonify({'success': False, 'message': 'آیتم متعلق به این میز نیست'}), 400
    
    table_item.quantity = quantity
    table_item.total_price = quantity * table_item.unit_price
    update_table_totals(table)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'تعداد به‌روزرسانی شد'})

# --- به‌روزرسانی اطلاعات مشتری میز ---
@table_bp.route('/<int:table_id>/update_customer', methods=['PUT'])
@login_required
def update_table_customer(table_id):
    table = Table.query.get_or_404(table_id)
    data = request.get_json()
    
    table.customer_name = data.get('customer_name', '')
    table.customer_phone = data.get('customer_phone', '')
    table.discount = int(data.get('discount', 0))
    
    # اگر تاریخ تولد ارسال شده و مشتری وجود دارد، آن را به‌روزرسانی کن
    birth_date_str = data.get('birth_date')
    if birth_date_str and table.customer_name:
        from datetime import datetime as dt
        try:
            birth_date = dt.strptime(birth_date_str, '%Y-%m-%d').date()
            # بررسی اینکه آیا مشتری موجود است یا نه
            customer = None
            if table.customer_phone:
                customer = Customer.query.filter_by(phone=table.customer_phone).first()
            if not customer and table.customer_name:
                customer = Customer.query.filter_by(name=table.customer_name).first()
            
            # اگر مشتری پیدا شد و سفارش قبلی ندارد، تاریخ تولد را اضافه کن
            if customer:
                from sqlalchemy import func
                order_count = db.session.query(func.count(Order.id)).filter_by(customer_id=customer.id).scalar()
                if order_count == 0 and not customer.birth_date:
                    # مشتری جدید است و تاریخ تولد ندارد
                    customer.birth_date = birth_date
        except (ValueError, TypeError):
            pass  # اگر تاریخ معتبر نبود، نادیده بگیر
    
    update_table_totals(table)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'اطلاعات به‌روزرسانی شد'})

# --- تابع کمکی برای به‌روزرسانی سفارش موجود ---
def update_existing_order(table, order):
    """به‌روزرسانی سفارش موجود با آیتم‌های جدید از TableItem یا OrderItem"""
    try:
        # دریافت TableItem های فعلی
        table_items = TableItem.query.filter_by(table_id=table.id).all()
        
        # ایجاد یا پیدا کردن مشتری
        # بررسی اینکه آیا مشتری موجود است
        customer = None
        birth_date = None
        if table.customer_phone:
            customer = Customer.query.filter_by(phone=table.customer_phone).first()
        if not customer and table.customer_name:
            customer = Customer.query.filter_by(name=table.customer_name).first()
        
        # اگر مشتری پیدا نشد، باید تاریخ تولد را از درخواست بگیریم
        data = request.get_json() or {}
        birth_date_str = data.get('birth_date')
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                birth_date = None
        
        customer = find_or_create_customer(
            table.customer_name or 'مشتری ناشناس',
            table.customer_phone,
            birth_date=birth_date
        )
        order.customer_id = customer.id
        order.discount = table.discount
        
        if not table_items:
            # اگر هیچ TableItem وجود ندارد، فقط مبلغ سفارش را به‌روزرسانی کن
            # (آیتم‌ها از OrderItem هستند و قبلاً حذف شده‌اند)
            update_order_totals(order)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'سفارش به‌روزرسانی شد',
                'order_id': order.id,
                'invoice_number': order.invoice_number,
                'daily_invoice_number': order.daily_sequence,
                'invoice_uid': order.invoice_uid
            })
        
        # حذف همه OrderItem های موجود (فیزیکی حذف نمی‌کنیم، فقط soft delete می‌کنیم)
        # اما برای سادگی، آیتم‌های جدید را اضافه می‌کنیم و آیتم‌های قدیمی را soft delete می‌کنیم
        existing_order_items = OrderItem.query.filter_by(order_id=order.id, is_deleted=False).all()
        
        # ایجاد یک دیکشنری از TableItem ها برای مقایسه
        table_items_dict = {}
        for item in table_items:
            key = (item.menu_item_id, item.unit_price)
            if key not in table_items_dict:
                table_items_dict[key] = []
            table_items_dict[key].append(item)
        
        # حذف OrderItem هایی که دیگر در TableItem نیستند
        for order_item in existing_order_items:
            key = (order_item.menu_item_id, order_item.unit_price)
            found = False
            if key in table_items_dict:
                # بررسی اینکه آیا این آیتم در TableItem وجود دارد
                for table_item in table_items_dict[key]:
                    if table_item.quantity == order_item.quantity:
                        found = True
                        table_items_dict[key].remove(table_item)
                        if not table_items_dict[key]:
                            del table_items_dict[key]
                        break
            
            if not found:
                # این آیتم دیگر وجود ندارد، soft delete کن
                order_item.is_deleted = True
                order_item.removal_reason = 'به‌روزرسانی سفارش'
        
        # افزودن آیتم‌های جدید از TableItem
        for table_item in table_items:
            # بررسی اینکه آیا این آیتم قبلاً در OrderItem وجود دارد یا نه
            existing = OrderItem.query.filter_by(
                order_id=order.id,
                menu_item_id=table_item.menu_item_id,
                unit_price=table_item.unit_price,
                is_deleted=False
            ).first()
            
            if existing:
                # اگر وجود دارد، فقط تعداد را به‌روزرسانی کن
                existing.quantity = table_item.quantity
                existing.total_price = table_item.quantity * table_item.unit_price
            else:
                # اگر وجود ندارد، جدید اضافه کن
                new_order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=table_item.menu_item_id,
                    quantity=table_item.quantity,
                    unit_price=table_item.unit_price,
                    total_price=table_item.total_price
                )
                db.session.add(new_order_item)
                db.session.flush()
                sync_order_item_material_usage(new_order_item)
            
            # کاهش موجودی
            menu_item = MenuItem.query.get(table_item.menu_item_id)
            if menu_item and menu_item.stock is not None:
                # فقط برای آیتم‌های جدید موجودی را کاهش بده
                # (برای آیتم‌های موجود، موجودی قبلاً کاهش یافته است)
                if not existing:
                    menu_item.stock = max(0, menu_item.stock - table_item.quantity)
        
        # به‌روزرسانی مبلغ سفارش
        update_order_totals(order)
        
        # حذف TableItem ها بعد از به‌روزرسانی
        TableItem.query.filter_by(table_id=table.id).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'سفارش به‌روزرسانی شد',
            'order_id': order.id,
            'invoice_number': order.invoice_number,
            'daily_invoice_number': order.daily_sequence,
            'invoice_uid': order.invoice_uid
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ خطا در به‌روزرسانی سفارش: {e}")
        return jsonify({'success': False, 'message': f'خطا در به‌روزرسانی سفارش: {str(e)}'}), 500

# --- ثبت یا به‌روزرسانی سفارش میز ---
@table_bp.route('/<int:table_id>/submit', methods=['POST'])
@login_required
def submit_table_order(table_id):
    try:
        table = Table.query.get_or_404(table_id)
        
        # اگر سفارش قبلاً ثبت شده باشد، باید به‌روزرسانی شود
        if table.order_id:
            order = Order.query.get(table.order_id)
            if order and order.status != 'پرداخت شده':
                # به‌روزرسانی سفارش موجود
                return update_existing_order(table, order)
        
        # اگر سفارش ثبت نشده باشد، ثبت جدید
        # بررسی وجود آیتم (فقط TableItem ها)
        table_items = TableItem.query.filter_by(table_id=table_id).all()
        if not table_items:
            return jsonify({'success': False, 'message': 'هیچ آیتمی برای ثبت وجود ندارد'}), 400
        
        # ایجاد یا پیدا کردن مشتری
        # بررسی اینکه آیا مشتری موجود است و تاریخ تولد دارد یا نه
        customer = None
        birth_date = None
        if table.customer_phone:
            customer = Customer.query.filter_by(phone=table.customer_phone).first()
        if not customer and table.customer_name:
            customer = Customer.query.filter_by(name=table.customer_name).first()
        
        # اگر مشتری پیدا نشد، باید تاریخ تولد را از درخواست بگیریم
        data = request.get_json() or {}
        birth_date_str = data.get('birth_date')
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                birth_date = None
        
        customer = find_or_create_customer(
            table.customer_name or 'مشتری ناشناس',
            table.customer_phone,
            birth_date=birth_date
        )
        
        # ایجاد سفارش
        invoice_identifiers = generate_invoice_number()
        settings = Settings.query.first()
        tax_percent = settings.tax_percent if settings else 9.0
        
        order_items_data = []
        for item in table_items:
            order_items_data.append({
                'menu_item_id': item.menu_item_id,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price
            })
            # کاهش موجودی
            menu_item = MenuItem.query.get(item.menu_item_id)
            if menu_item and menu_item.stock is not None:
                menu_item.stock = max(0, menu_item.stock - item.quantity)
        
        total, tax, final = calculate_order_amount(order_items_data, table.discount, tax_percent)
        
        iran_tz = pytz.timezone('Asia/Tehran')
        order = Order(
            invoice_number=invoice_identifiers.unique_number,
            daily_sequence=invoice_identifiers.daily_sequence,
            invoice_uid=invoice_identifiers.invoice_uid,
            customer_id=customer.id,
            total_amount=total,
            discount=table.discount,
            tax_amount=tax,
            final_amount=final,
            status='پرداخت نشده',
            type='حضوری',
            user_id=current_user.id,
            created_at=datetime.now(iran_tz)
        )
        
        db.session.add(order)
        db.session.flush()
        
        # افزودن آیتم‌های سفارش
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data['menu_item_id'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['total_price']
            )
            db.session.add(order_item)

        db.session.flush()
        for order_item in order.order_items:
            sync_order_item_material_usage(order_item)
        
        # اتصال سفارش به میز
        table.order_id = order.id
        order.table_id = table_id
        
        # حذف TableItem ها بعد از ثبت سفارش
        TableItem.query.filter_by(table_id=table_id).delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'سفارش با موفقیت ثبت شد',
            'order_id': order.id,
            'invoice_number': order.invoice_number,
            'daily_invoice_number': order.daily_sequence,
            'invoice_uid': order.invoice_uid
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ خطا در ثبت سفارش میز: {e}")
        return jsonify({'success': False, 'message': f'خطا در ثبت سفارش: {str(e)}'}), 500

# --- تسویه میز ---
@table_bp.route('/<int:table_id>/checkout', methods=['POST'])
@login_required
def checkout_table(table_id):
    table = Table.query.get_or_404(table_id)
    data = request.get_json()
    
    if not table.order_id:
        return jsonify({'success': False, 'message': 'ابتدا باید سفارش ثبت شود'}), 400
    
    order = Order.query.get(table.order_id)
    if not order:
        return jsonify({'success': False, 'message': 'سفارش یافت نشد'}), 404
    
    # به‌روزرسانی وضعیت سفارش
    order.status = 'پرداخت شده'
    order.paid_at = datetime.now(pytz.timezone('Asia/Tehran'))
    order.payment_method = data.get('payment_method', 'کارتخوان')
    
    # پاک کردن میز
    TableItem.query.filter_by(table_id=table_id).delete()
    table.status = 'خالی'
    table.customer_name = None
    table.customer_phone = None
    table.order_id = None
    table.total_amount = 0
    table.discount = 0
    table.tax_amount = 0
    table.final_amount = 0
    table.started_at = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'میز تسویه شد',
        'invoice_number': order.invoice_number,
        'daily_invoice_number': order.daily_sequence,
        'invoice_uid': order.invoice_uid
    })

# --- تابع کمکی برای به‌روزرسانی مبلغ کل میز ---
def update_table_totals(table):
    table_items = TableItem.query.filter_by(table_id=table.id).all()
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    
    order_items_data = [{
        'quantity': item.quantity,
        'unit_price': item.unit_price
    } for item in table_items]
    
    total, tax, final = calculate_order_amount(order_items_data, table.discount, tax_percent)
    
    table.total_amount = total
    table.tax_amount = tax
    table.final_amount = final
    table.updated_at = datetime.now(pytz.timezone('Asia/Tehran'))

def update_order_totals(order):
    # فقط آیتم‌های حذف نشده را در نظر بگیر
    order_items = OrderItem.query.filter_by(order_id=order.id, is_deleted=False).all()
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    
    order_items_data = [{
        'quantity': item.quantity,
        'unit_price': item.unit_price
    } for item in order_items]
    
    total, tax, final = calculate_order_amount(order_items_data, order.discount, tax_percent)
    
    order.total_amount = total
    order.tax_amount = tax
    order.final_amount = final

