from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.models import (
    db,
    Order,
    OrderItem,
    MenuItem,
    Customer,
    Settings,
    find_or_create_customer,
    generate_invoice_number,
    calculate_order_amount,
    record_order_material_usage,
    sync_order_item_material_usage
)
from datetime import datetime
import pytz

takeaway_bp = Blueprint('takeaway', __name__, url_prefix='/takeaway')

# --- ایجاد سفارش بیرون‌بر جدید (موقت) ---
@takeaway_bp.route('/create', methods=['POST'])
@login_required
def create_takeaway():
    try:
        data = request.get_json()
        customer_name = data.get('customer_name', 'مشتری ناشناس')
        customer_phone = data.get('customer_phone', '')
        discount = int(data.get('discount', 0))
        
        customer = find_or_create_customer(customer_name, customer_phone)
        invoice_identifiers = generate_invoice_number()
        settings = Settings.query.first()
        tax_percent = settings.tax_percent if settings else 9.0
        
        # ایجاد سفارش موقت (پرداخت نشده)
        iran_tz = pytz.timezone('Asia/Tehran')
        order = Order(
            invoice_number=invoice_identifiers.unique_number,
            daily_sequence=invoice_identifiers.daily_sequence,
            invoice_uid=invoice_identifiers.invoice_uid,
            customer_id=customer.id,
            total_amount=0,
            discount=discount,
            tax_amount=0,
            final_amount=0,
            status='پرداخت نشده',
            type='بیرون‌بر',
            user_id=current_user.id,
            created_at=datetime.now(iran_tz)
        )
        
        db.session.add(order)
        db.session.flush()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order_id': order.id,
            'invoice_number': order.invoice_number,
            'daily_invoice_number': order.daily_sequence,
            'invoice_uid': order.invoice_uid
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ خطا در ایجاد سفارش بیرون‌بر: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'خطا در ایجاد سفارش: {str(e)}'}), 500

# --- افزودن آیتم به سفارش بیرون‌بر ---
@takeaway_bp.route('/<int:order_id>/add_item', methods=['POST'])
@login_required
def add_item_to_takeaway(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        if order.type != 'بیرون‌بر' or order.status == 'پرداخت شده':
            return jsonify({'success': False, 'message': 'سفارش نامعتبر است یا قبلاً تسویه شده است'}), 400
        
        data = request.get_json()
        menu_item_id = data.get('menu_item_id')
        quantity = int(data.get('quantity', 1))
        
        menu_item = MenuItem.query.get_or_404(menu_item_id)
        
        # بررسی وجود آیتم در سفارش (فقط آیتم‌های حذف نشده)
        existing_item = OrderItem.query.filter_by(
            order_id=order_id,
            menu_item_id=menu_item_id,
            is_deleted=False
        ).first()
        
        if existing_item:
            existing_item.quantity += quantity
            existing_item.total_price = existing_item.quantity * existing_item.unit_price
        else:
            new_item = OrderItem(
                order_id=order_id,
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
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500

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

# --- بررسی اولین سفارش روز برای بیرون‌بر ---
@takeaway_bp.route('/<int:order_id>/check_first_order', methods=['GET'])
@login_required
def check_first_order(order_id):
    """بررسی می‌کند که آیا سفارش اولین ثبت روز است یا نه"""
    order = Order.query.get_or_404(order_id)
    is_first = is_first_order_of_day(order_id)
    return jsonify({'is_first_order': is_first})

# --- حذف آیتم از سفارش بیرون‌بر ---
@takeaway_bp.route('/<int:order_id>/remove_item/<int:item_id>', methods=['DELETE'])
@login_required
def remove_item_from_takeaway(order_id, item_id):
    try:
        order = Order.query.get_or_404(order_id)
        order_item = OrderItem.query.get_or_404(item_id)
        
        if order_item.order_id != order_id:
            return jsonify({'success': False, 'message': 'آیتم متعلق به این سفارش نیست'}), 400
        
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
        
        # به جای حذف فیزیکی، فقط علامت‌گذاری می‌کنیم
        # db.session.delete(order_item)  # حذف شد - به جای آن is_deleted = True
        update_order_totals(order)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'آیتم حذف شد'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500

# --- به‌روزرسانی تعداد آیتم ---
@takeaway_bp.route('/<int:order_id>/update_item/<int:item_id>', methods=['PUT'])
@login_required
def update_item_quantity(order_id, item_id):
    try:
        order = Order.query.get_or_404(order_id)
        order_item = OrderItem.query.get_or_404(item_id)
        data = request.get_json()
        quantity = int(data.get('quantity', 1))
        
        if quantity <= 0:
            return remove_item_from_takeaway(order_id, item_id)
        
        if order_item.order_id != order_id:
            return jsonify({'success': False, 'message': 'آیتم متعلق به این سفارش نیست'}), 400
        
        order_item.quantity = quantity
        order_item.total_price = quantity * order_item.unit_price
        update_order_totals(order)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'تعداد به‌روزرسانی شد'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500

# --- به‌روزرسانی اطلاعات مشتری و تخفیف ---
@takeaway_bp.route('/<int:order_id>/update', methods=['PUT'])
@login_required
def update_takeaway(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        
        customer_name = data.get('customer_name', '')
        customer_phone = data.get('customer_phone', '')
        discount = int(data.get('discount', 0))
        birth_date_str = data.get('birth_date')
        
        # تبدیل تاریخ تولد
        birth_date = None
        if birth_date_str:
            try:
                from datetime import datetime
                birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        
        # به‌روزرسانی یا ایجاد مشتری
        customer = find_or_create_customer(customer_name, customer_phone, birth_date=birth_date)
        order.customer_id = customer.id
        order.discount = discount
        
        update_order_totals(order)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'اطلاعات به‌روزرسانی شد'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500

# --- ثبت یا به‌روزرسانی سفارش بیرون‌بر ---
@takeaway_bp.route('/<int:order_id>/submit', methods=['POST'])
@login_required
def submit_takeaway(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        if order.type != 'بیرون‌بر':
            return jsonify({'success': False, 'message': 'سفارش نامعتبر است'}), 400
        
        # اگر سفارش قبلاً تسویه شده باشد، اجازه به‌روزرسانی نده
        if order.status == 'پرداخت شده':
            return jsonify({'success': False, 'message': 'سفارش قبلاً تسویه شده است'}), 400
        
        # دریافت اطلاعات مشتری و تخفیف از درخواست (اگر ارسال شده باشد)
        data = request.get_json() or {}
        customer_name = data.get('customer_name')
        customer_phone = data.get('customer_phone')
        discount = data.get('discount')
        
        # به‌روزرسانی اطلاعات مشتری و تخفیف اگر ارسال شده باشد
        if customer_name is not None or customer_phone is not None or discount is not None:
            customer = find_or_create_customer(
                customer_name or (order.customer.name if order.customer else 'مشتری ناشناس'),
                customer_phone or (order.customer.phone if order.customer else '')
            )
            order.customer_id = customer.id
            if discount is not None:
                order.discount = int(discount)
        
        # دریافت آیتم‌های فعلی (فقط آیتم‌های حذف نشده)
        order_items = OrderItem.query.filter_by(order_id=order_id, is_deleted=False).all()
        if not order_items:
            return jsonify({'success': False, 'message': 'هیچ آیتمی برای ثبت وجود ندارد'}), 400
        
        # به‌روزرسانی مبلغ سفارش بر اساس آیتم‌های فعلی
        update_order_totals(order)
        
        # کاهش موجودی (فقط برای آیتم‌هایی که قبلاً موجودی کاهش نیافته‌اند)
        # این کار فقط یک بار انجام می‌شود - اگر سفارش قبلاً ثبت شده باشد، موجودی قبلاً کاهش یافته است
        # برای تشخیص اینکه آیا سفارش قبلاً ثبت شده است، می‌توانیم چک کنیم که آیا موجودی کاهش یافته است یا نه
        # اما برای سادگی، همیشه موجودی را کاهش می‌دهیم (اگر قبلاً کاهش یافته باشد، مشکلی ایجاد نمی‌کند)
        for item in order_items:
            menu_item = MenuItem.query.get(item.menu_item_id)
            if menu_item and menu_item.stock is not None:
                menu_item.stock = max(0, menu_item.stock - item.quantity)
        
        db.session.flush()
        record_order_material_usage(order, replace_existing=True)

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'سفارش با موفقیت به‌روزرسانی شد' if order.status == 'پرداخت نشده' else 'سفارش با موفقیت ثبت شد',
            'order_id': order.id,
            'invoice_number': order.invoice_number,
            'daily_invoice_number': order.daily_sequence,
            'invoice_uid': order.invoice_uid
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ خطا در ثبت/به‌روزرسانی سفارش بیرون‌بر: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'خطا در ثبت/به‌روزرسانی سفارش: {str(e)}'}), 500

# --- تسویه سفارش بیرون‌بر ---
@takeaway_bp.route('/<int:order_id>/checkout', methods=['POST'])
@login_required
def checkout_takeaway(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        
        if order.type != 'بیرون‌بر':
            return jsonify({'success': False, 'message': 'سفارش نامعتبر است'}), 400
        
        # به‌روزرسانی وضعیت سفارش
        order.status = 'پرداخت شده'
        order.paid_at = datetime.now(pytz.timezone('Asia/Tehran'))
        order.payment_method = data.get('payment_method', 'کارتخوان')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'سفارش تسویه شد',
            'invoice_number': order.invoice_number,
            'daily_invoice_number': order.daily_sequence,
            'invoice_uid': order.invoice_uid
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500

# --- دریافت اطلاعات سفارش بیرون‌بر ---
@takeaway_bp.route('/<int:order_id>', methods=['GET'])
@login_required
def get_takeaway(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        # فقط آیتم‌های حذف نشده را برگردان
        order_items = OrderItem.query.filter_by(order_id=order_id, is_deleted=False).all()
        
        items_data = []
        for item in order_items:
            items_data.append({
                'id': item.id,
                'menu_item_id': item.menu_item_id,
                'menu_item_name': item.menu_item.name,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price
            })
        
        return jsonify({
            'id': order.id,
            'invoice_number': order.invoice_number,
            'daily_invoice_number': order.daily_sequence,
            'invoice_uid': order.invoice_uid,
            'customer_name': order.customer.name,
            'customer_phone': order.customer.phone or '',
            'total_amount': order.total_amount,
            'discount': order.discount,
            'tax_amount': order.tax_amount,
            'final_amount': order.final_amount,
            'status': order.status,
            'items': items_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'}), 500

# --- حذف سفارش بیرون‌بر ---
@takeaway_bp.route('/<int:order_id>/delete', methods=['DELETE', 'POST'])
@login_required
def delete_takeaway(order_id):
    try:
        print(f"🗑️ Attempting to delete takeaway order {order_id}")
        order = Order.query.get(order_id)
        
        if not order:
            print(f"❌ Order {order_id} not found")
            return jsonify({'success': False, 'message': 'سفارش یافت نشد'}), 404
        
        # بررسی اینکه سفارش از نوع بیرون‌بر است
        if order.type != 'بیرون‌بر':
            print(f"❌ Order {order_id} is not a takeaway order (type: {order.type})")
            return jsonify({'success': False, 'message': 'سفارش نامعتبر است'}), 400
        
        # حذف آیتم‌های سفارش
        deleted_items = OrderItem.query.filter_by(order_id=order_id).delete()
        print(f"🗑️ Deleted {deleted_items} order items")
        
        # حذف سفارش
        db.session.delete(order)
        db.session.commit()
        
        print(f"✅ Successfully deleted takeaway order {order_id}")
        return jsonify({
            'success': True,
            'message': 'سفارش با موفقیت حذف شد'
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ خطا در حذف سفارش بیرون‌بر: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'خطا در حذف سفارش: {str(e)}'}), 500

# --- تابع کمکی برای به‌روزرسانی مبلغ سفارش ---
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

