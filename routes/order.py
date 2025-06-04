from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models.models import db, MenuItem, Order, OrderItem, Customer, Settings, find_or_create_customer, generate_invoice_number, calculate_order_amount
from sqlalchemy import func
from datetime import datetime
import pytz
import win32print
import win32ui

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
        orders_query = orders_query.join(Customer).filter(
            (Order.invoice_number == q) |
            (Customer.name.ilike(f'%{q}%')) |
            (Customer.phone.ilike(f'%{q}%'))
        )
    orders = orders_query.order_by(Order.created_at.desc()).all()
    return render_template('orders/orders_list.html', orders=orders, q=q, status=status)

# --- ثبت سفارش جدید (فرم) ---
@order_bp.route('/order/new')
@login_required # Added login_required as it's likely needed for creating orders
def new_order_form():
    menu_items = MenuItem.query.all()
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
    invoice_number = generate_invoice_number()
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
        invoice_number=invoice_number,
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

    db.session.commit()
    print_invoice(order)
    flash(f'سفارش با شماره فاکتور {order.invoice_number} با موفقیت ثبت شد!', 'success')
    return jsonify(success=True, order_id=order.id)
# --- نمایش جزئیات سفارش ---
@order_bp.route('/order/<int:order_id>') # Added route for detail page
@login_required # Added login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('orders/order_detail.html', order=order)

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
    order.payment_method = request.form.get('payment_method', 'نقدی')
    db.session.commit()
    flash('سفارش با موفقیت پرداخت شد.', 'success')
    return redirect(url_for('order.order_detail', order_id=order.id))

# --- حذف سفارش ---
@order_bp.route('/order/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    # حذف آیتم‌های وابسته به سفارش
    OrderItem.query.filter_by(order_id=order.id).delete()
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for('order.orders_report'))

# --- ویرایش سفارش (فرم و ذخیره) ---
@order_bp.route('/order/<int:order_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    order = Order.query.get_or_404(order_id)
    menu_items = MenuItem.query.filter_by(is_active=True).all()
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    if request.method == 'POST':
        # ویرایش اطلاعات سفارش
        order.discount = int(request.form.get('discount', 0))
        order.type = request.form.get('type', order.type)
        order.status = request.form.get('status', order.status)
        # ویرایش آیتم‌های سفارش
        db.session.query(OrderItem).filter_by(order_id=order.id).delete()
        items = request.form.getlist('item')
        quantities = request.form.getlist('quantity')
        order_items = []
        for item_id, qty in zip(items, quantities):
            menu_item = MenuItem.query.get(int(item_id))
            qty = int(qty)
            if menu_item and qty > 0: # Ensure item exists and quantity is positive
                order_items.append({
                    'menu_item_id': menu_item.id,
                    'quantity': qty,
                    'unit_price': int(menu_item.price),
                    'total_price': int(menu_item.price * qty)
                })
            else:
                 flash(f'آیتم با شناسه {item_id} نامعتبر است یا تعداد آن صفر است.', 'warning')
                 # Optionally, you might want to break or handle this more strictly

        if not order_items: # Check if any valid items were added
            flash('هیچ آیتم معتبری برای ویرایش سفارش وجود ندارد.', 'danger')
            return redirect(url_for('order.edit_order', order_id=order.id))


        total, tax, final = calculate_order_amount(order_items, order.discount, tax_percent)
        order.total_amount = total
        order.tax_amount = tax
        order.final_amount = final
        for oi in order_items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=oi['menu_item_id'],
                quantity=oi['quantity'],
                unit_price=oi['unit_price'],
                total_price=oi['total_price']
            )
            db.session.add(order_item)
        db.session.commit()
        flash('سفارش ویرایش شد.', 'success')
        return redirect(url_for('order.order_detail', order_id=order.id))
    return render_template('orders/edit_order.html', order=order, menu_items=menu_items, tax_percent=tax_percent)

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
    
    # کم کردن موجودی آیتم منو
    if menu_item.stock is not None:
        menu_item.stock = max(menu_item.stock - quantity, 0)
        db.session.add(menu_item)
    
    # Recalculate order totals after adding item
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    order_items_data = [{
        'menu_item_id': item.menu_item_id,
        'quantity': item.quantity,
        'unit_price': item.unit_price,
        'total_price': item.total_price
    } for item in order.order_items] # Get existing items + the new one added to session
    total, tax, final = calculate_order_amount(order_items_data, order.discount, tax_percent)
    order.total_amount = total
    order.tax_amount = tax
    order.final_amount = final

    db.session.commit()
    flash('آیتم به سفارش اضافه شد.', 'success')
    return redirect(url_for('order.order_detail', order_id=order.id))

# --- حذف آیتم از سفارش (AJAX) ---
@order_bp.route('/order/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_order_item(item_id):
    order_item = OrderItem.query.get_or_404(item_id)
    order_id = order_item.order_id
    order = order_item.order # Get the parent order before deleting the item
    db.session.delete(order_item)
    db.session.commit() # Commit deletion first

    # Recalculate order totals after deleting item
    settings = Settings.query.first()
    tax_percent = settings.tax_percent if settings else 9.0
    order_items_data = [{
        'menu_item_id': item.menu_item_id,
        'quantity': item.quantity,
        'unit_price': item.unit_price,
        'total_price': item.total_price
    } for item in order.order_items] # Get remaining items

    # Handle case where all items are deleted
    if not order_items_data:
        order.total_amount = 0
        order.tax_amount = 0
        order.final_amount = 0
    else:
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
        results.append({
            'id': c.id,
            'name': c.name,
            'phone': c.phone
        })
    return jsonify(results)

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
        invoice_number = generate_invoice_number()
        
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
            invoice_number=invoice_number,
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
        
        return jsonify({'success': True, 'order_id': order.id, 'updatedStocks': updated_stocks})
        
    except Exception as e:
        print("❌ خطای ثبت سفارش:", e)
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطای داخلی سرور'}), 500

@order_bp.route('/api/menu_stock')
@login_required
def api_menu_stock():
    items = MenuItem.query.filter_by(is_active=True).all()
    return jsonify([
        {'id': item.id, 'stock': item.stock}
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



def print_invoice(order):
    invoice_text = f"""فاکتور شماره: {order.invoice_number}
تاریخ: {order.created_at.strftime('%Y-%m-%d %H:%M')}
مشتری: {order.customer.name}
-------------------------------
"""
    for item in order.order_items:
        invoice_text += f"{item.menu_item.name} x{item.quantity} = {item.total_price} تومان\n"
    invoice_text += "-------------------------------\n"
    invoice_text += f"جمع کل: {order.total_amount} تومان\n"
    invoice_text += f"تخفیف: {order.discount} تومان\n"
    invoice_text += f"مالیات: {order.tax_amount} تومان\n"
    invoice_text += f"مبلغ نهایی: {order.final_amount} تومان\n"
    invoice_text += "\nبا تشکر 🌸"

    printer_name = win32print.GetDefaultPrinter()
    hprinter = win32print.OpenPrinter(printer_name)
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)
    hdc.StartDoc("Cafe Invoice")
    hdc.StartPage()
    hdc.TextOut(100, 100, invoice_text)
    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()