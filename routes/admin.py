from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask import current_app as app
from flask_login import login_required, current_user
from models.models import db, Settings, Order, Customer, User
from sqlalchemy import func, extract
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# --- داشبورد مدیریتی ---
@admin_bp.route('/dashboard')
@login_required
def dashboard():
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
    if request.method == 'POST':
        tax_percent = float(request.form['tax_percent'])
        cafe_name = request.form.get('cafe_name')
        address = request.form.get('address')
        phone = request.form.get('phone')
        logo_url = request.form.get('logo_url')
        if settings:
            settings.tax_percent = tax_percent
            settings.cafe_name = cafe_name
            settings.address = address
            settings.phone = phone
            settings.logo_url = logo_url
            settings.updated_at = datetime.utcnow()
        else:
            settings = Settings(
                tax_percent=tax_percent,
                cafe_name=cafe_name,
                address=address,
                phone=phone,
                logo_url=logo_url,
                updated_at=datetime.utcnow()
            )
            db.session.add(settings)
        db.session.commit()
        flash('تنظیمات با موفقیت ذخیره شد.', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html', settings=settings)

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
        orders_query = orders_query.join(Customer).filter(
            (Order.invoice_number == q) |
            (Customer.name.ilike(f'%{q}%')) |
            (Customer.phone.ilike(f'%{q}%'))
        )
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
    order.payment_method = request.form.get('payment_method', 'نقدی')
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
    period = request.args.get('period', 'week')
    today = datetime.now().date()
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today.replace(day=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today - timedelta(days=7)

    orders = Order.query.filter(Order.created_at >= start_date).all()
    total_sales = sum(o.final_amount for o in orders)
    total_discount = sum(o.discount for o in orders)
    total_tax = sum(o.tax_amount for o in orders)
    paid_orders = [o for o in orders if o.status == 'پرداخت شده']
    unpaid_orders = [o for o in orders if o.status == 'پرداخت نشده']

    return render_template('admin/financial_report.html',
                           orders=orders,
                           total_sales=total_sales,
                           total_discount=total_discount,
                           total_tax=total_tax,
                           paid_orders=paid_orders,
                           unpaid_orders=unpaid_orders,
                           period=period)

# --- مدیریت کاربران (لیست، افزودن، ویرایش، حذف) ---
@admin_bp.route('/users')
@login_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # هش کردن رمز عبور را باید اضافه کنی
        name = request.form.get('name')
        role = request.form.get('role', 'waiter')
        phone = request.form.get('phone')
        if User.query.filter_by(username=username).first():
            flash('این نام کاربری قبلاً ثبت شده است.', 'danger')
            return redirect(url_for('admin.add_user'))
        user = User(username=username, password_hash=password, name=name, role=role, phone=phone)
        db.session.add(user)
        db.session.commit()
        flash('کاربر جدید با موفقیت اضافه شد.', 'success')
        return redirect(url_for('admin.users_list'))
    return render_template('admin/add_user.html')

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
    return render_template('admin/edit_user.html', user=user)

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
    orders = Order.query.join(Customer).filter(
        (Order.invoice_number == q) |
        (Customer.name.ilike(f'%{q}%')) |
        (Customer.phone.ilike(f'%{q}%'))
    ).all()
    results = []
    for o in orders:
        results.append({
            'id': o.id,
            'invoice_number': o.invoice_number,
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