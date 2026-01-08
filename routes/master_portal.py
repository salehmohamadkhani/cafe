from __future__ import annotations

from datetime import datetime
import pytz

import os
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from models.models import db
from models.master_models import CafeModule, CafeTenant, MasterUser, UserCreationRequest
import shutil
from services.tenant_provisioning import provision_tenant
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import User as TenantUser

master_bp = Blueprint('master', __name__, url_prefix='/master')

# Registry of available modules
MODULES = [
    ("orders", "Orders/POS"),
    ("inventory", "Inventory"),
    ("accounting", "Accounting"),
    ("customers", "Customers/CRM"),
    ("reports", "Reports"),
    ("menu", "Menu"),
    ("users", "Users & Roles"),
]


def _master_user() -> MasterUser | None:
    user_id = session.get('master_user_id')
    if not user_id:
        return None
    try:
        return MasterUser.query.get(int(user_id))
    except Exception:
        return None


def master_login_required(view_func):
    def wrapper(*args, **kwargs):
        user = _master_user()
        if not user or not user.is_active:
            return redirect(url_for('master.login', next=request.path))
        return view_func(*args, **kwargs)

    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


@master_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone_number = (request.form.get('phone_number') or '').strip()
        password = (request.form.get('password') or '').strip()
        
        if not phone_number:
            flash('شماره موبایل الزامی است.', 'danger')
            return render_template('master/login.html', phone_number=phone_number)
        
        if not password:
            flash('رمز عبور الزامی است.', 'danger')
            return render_template('master/login.html', phone_number=phone_number)
        
        # بررسی رمز عبور (123)
        if password != '123':
            flash('رمز عبور اشتباه است.', 'danger')
            return render_template('master/login.html', phone_number=phone_number)
        
        # نرمال‌سازی شماره موبایل
        phone_normalized = phone_number.replace(' ', '').replace('-', '').replace('+', '')
        if phone_normalized.startswith('0'):
            phone_normalized = '98' + phone_normalized[1:]
        elif not phone_normalized.startswith('98'):
            phone_normalized = '98' + phone_normalized
        
        # پیدا کردن یا ایجاد کاربر
        user = MasterUser.query.filter_by(phone_number=phone_normalized).first()
        if not user:
            # ایجاد کاربر جدید
            user = MasterUser(
                phone_number=phone_normalized,
                username=phone_normalized,  # استفاده از شماره به عنوان username
                role='superadmin',
                is_active=True
            )
            db.session.add(user)
            db.session.flush()
        
        if not user.is_active:
            flash('این حساب غیرفعال است.', 'danger')
            return render_template('master/login.html', phone_number=phone_number)
        
        # ورود کاربر
        session['master_user_id'] = int(user.id)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        next_url = request.args.get('next')
        return redirect(next_url or url_for('master.dashboard'))
    
    return render_template('master/login.html')


@master_bp.route('/logout')
def logout():
    session.pop('master_user_id', None)
    return redirect(url_for('master.login'))


@master_bp.route('/')
@master_login_required
def dashboard():
    user = _master_user()
    cafes = CafeTenant.query.order_by(CafeTenant.created_at.desc()).all()
    
    # Collect summary statistics for each cafe
    cafe_stats = []
    total_orders = 0
    total_revenue = 0
    active_cafes = 0
    
    for cafe in cafes:
        stats = {
            'cafe': cafe,
            'orders_count': 0,
            'revenue': 0,
            'users_count': 0,
            'menu_items_count': 0,
            'customers_count': 0,
            'has_data': False
        }
        
        if cafe.is_active and os.path.exists(cafe.db_path):
            try:
                engine = create_engine(f"sqlite:///{cafe.db_path}")
                Session = sessionmaker(bind=engine)
                with Session() as s:
                    from models.models import Order, User, MenuItem, Customer
                    from sqlalchemy import func
                    
                    stats['orders_count'] = s.query(func.count(Order.id)).scalar() or 0
                    stats['revenue'] = s.query(func.coalesce(func.sum(Order.final_amount), 0)).filter(Order.status == 'پرداخت شده').scalar() or 0
                    stats['users_count'] = s.query(func.count(User.id)).scalar() or 0
                    stats['menu_items_count'] = s.query(func.count(MenuItem.id)).scalar() or 0
                    stats['customers_count'] = s.query(func.count(Customer.id)).scalar() or 0
                    stats['has_data'] = True
                    
                    total_orders += stats['orders_count']
                    total_revenue += stats['revenue']
            except Exception as e:
                stats['error'] = str(e)
        
        if cafe.is_active:
            active_cafes += 1
        
        cafe_stats.append(stats)
    
    summary = {
        'total_cafes': len(cafes),
        'active_cafes': active_cafes,
        'inactive_cafes': len(cafes) - active_cafes,
        'total_orders': total_orders,
        'total_revenue': total_revenue
    }
    
    # Get user creation requests for the requests tab
    user_requests = UserCreationRequest.query.order_by(UserCreationRequest.created_at.desc()).all()
    # Get cafe names for each request
    for req in user_requests:
        req.cafe = CafeTenant.query.get(req.cafe_id)
    
    return render_template('master/dashboard.html', master_user=user, cafes=cafes, modules=MODULES, cafe_stats=cafe_stats, summary=summary, user_requests=user_requests)


@master_bp.route('/cafes/create', methods=['POST'])
@master_login_required
def create_cafe():
    name = (request.form.get('name') or '').strip()
    slug = (request.form.get('slug') or '').strip()

    tenants_dir = current_app.config.get('TENANTS_DIR')
    if not tenants_dir:
        tenants_dir = current_app.config.get('CAFE_TENANTS_DIR')  # fallback

    # Source project directory (current project root)
    source_dir = current_app.config.get('BASEDIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    try:
        provisioned = provision_tenant(
            tenants_dir=tenants_dir,
            name=name,
            slug=slug,
            source_project_dir=source_dir
        )
    except Exception as exc:
        flash(f'خطا در ساخت کافه: {exc}', 'danger')
        return redirect(url_for('master.dashboard'))

    # Register in master DB
    existing = CafeTenant.query.filter_by(slug=provisioned.slug).first()
    if existing:
        flash('این کد/slug قبلاً ثبت شده است.', 'warning')
        return redirect(url_for('master.dashboard'))

    cafe = CafeTenant(
        name=provisioned.name,
        slug=provisioned.slug,
        root_dir=provisioned.root_dir,
        db_path=provisioned.db_path,
        is_active=True,
    )
    db.session.add(cafe)
    db.session.flush()  # Get cafe.id before commit

    # Process selected modules
    selected_modules = request.form.getlist("modules")
    selected_set = set(selected_modules)

    # Create CafeModule rows for ALL modules in registry
    for module_code, _ in MODULES:
        is_enabled = module_code in selected_set
        module = CafeModule(
            cafe_id=cafe.id,
            module_code=module_code,
            is_enabled=is_enabled
        )
        db.session.add(module)

    db.session.commit()

    flash(f'کافه «{cafe.name}» ساخته شد.', 'success')
    return redirect(url_for('master.dashboard'))


@master_bp.route('/cafes/<slug>/enter')
@master_login_required
def enter_cafe(slug):
    """نمایش اطلاعات لاگین کافه و لینک ورود"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    if not cafe.is_active:
        flash('این کافه غیرفعال است.', 'warning')
        return redirect(url_for('master.dashboard'))
    
    if not os.path.exists(cafe.db_path):
        flash('دیتابیس کافه یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    # Redirect to tenant login page
    return redirect(url_for('tenant_auth.login', slug=slug))


@master_bp.route('/cafes/<slug>/users')
@master_login_required
def cafe_users(slug):
    """لیست کاربران یک کافه (از master portal)"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    if not os.path.exists(cafe.db_path):
        flash('دیتابیس کافه یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    # Connect to tenant DB
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    with Session() as s:
        users = s.query(TenantUser).order_by(TenantUser.created_at.desc()).all()
        users_data = [{
            'id': u.id,
            'username': u.username,
            'name': u.name,
            'role': u.role,
            'is_active': u.is_active
        } for u in users]
    
    return render_template('master/cafe_users.html', cafe=cafe, users=users_data)


@master_bp.route('/cafes/<slug>/users/delete-all-except-admin', methods=['POST'])
@master_login_required
def delete_all_users_except_admin(slug):
    """حذف تمام کاربران به جز admin از دیتابیس کافه"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    if not os.path.exists(cafe.db_path):
        flash('دیتابیس کافه یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    # Connect to tenant DB
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    try:
        with Session() as s:
            # پیدا کردن همه کاربران به جز admin
            users_to_delete = s.query(TenantUser).filter(TenantUser.role != 'admin').all()
            count = len(users_to_delete)
            
            for user in users_to_delete:
                s.delete(user)
            
            s.commit()
            flash(f'{count} کاربر به جز admin از دیتابیس حذف شدند.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting users for cafe {slug}: {e}", exc_info=True)
        flash(f'خطا در حذف کاربران: {str(e)}', 'danger')
    
    return redirect(url_for('master.cafe_users', slug=slug))


@master_bp.route('/cafes/<slug>/users/<int:user_id>/delete', methods=['POST'])
@master_login_required
def delete_cafe_user(slug, user_id):
    """حذف یک کاربر خاص از دیتابیس کافه"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    if not os.path.exists(cafe.db_path):
        flash('دیتابیس کافه یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    # Connect to tenant DB
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    try:
        with Session() as s:
            user = s.query(TenantUser).get(user_id)
            if not user:
                flash('کاربر یافت نشد.', 'warning')
                return redirect(url_for('master.cafe_users', slug=slug))
            
            if user.role == 'admin':
                flash('نمی‌توانید کاربر admin را حذف کنید.', 'warning')
                return redirect(url_for('master.cafe_users', slug=slug))
            
            username = user.username
            s.delete(user)
            s.commit()
            flash(f'کاربر «{username}» از دیتابیس حذف شد.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting user {user_id} from cafe {slug}: {e}", exc_info=True)
        flash(f'خطا در حذف کاربر: {str(e)}', 'danger')
    
    return redirect(url_for('master.cafe_users', slug=slug))


@master_bp.route('/cafes/<slug>/users/<int:user_id>/report')
@master_login_required
def user_report(slug, user_id):
    """گزارش و لاگ کامل کاربر"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    if not os.path.exists(cafe.db_path):
        flash('دیتابیس کافه یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    # Connect to tenant DB
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    with Session() as s:
        from models.models import ActionLog, Order
        from sqlalchemy import func
        
        # اطلاعات کاربر
        user = s.query(TenantUser).get(user_id)
        if not user:
            flash('کاربر یافت نشد.', 'warning')
            return redirect(url_for('master.cafe_users', slug=slug))
        
        # لاگ فعالیت‌های کاربر
        action_logs = s.query(ActionLog).filter_by(user_id=user_id).order_by(ActionLog.timestamp.desc()).limit(100).all()
        
        # سفارش‌های ایجاد شده توسط کاربر
        orders = s.query(Order).filter_by(user_id=user_id).order_by(Order.created_at.desc()).limit(50).all()
        
        # آمار کلی
        total_orders = s.query(func.count(Order.id)).filter_by(user_id=user_id).scalar() or 0
        total_actions = s.query(func.count(ActionLog.id)).filter_by(user_id=user_id).scalar() or 0
        
        # زمان‌های ورود (از لاگ‌ها)
        login_times = []
        for log in action_logs:
            if 'login' in log.action.lower() or 'ورود' in (log.details or ''):
                login_times.append(log.timestamp)
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'role': user.role,
            'phone': user.phone,
            'is_active': user.is_active,
            'created_at': user.created_at,
            'last_login': user.last_login
        }
        
        logs_data = [{
            'id': log.id,
            'action': log.action,
            'target_type': log.target_type,
            'target_id': log.target_id,
            'timestamp': log.timestamp,
            'details': log.details
        } for log in action_logs]
        
        orders_data = [{
            'id': order.id,
            'invoice_number': str(order.invoice_number) if order.invoice_number else '-',
            'final_amount': order.final_amount or 0,
            'status': order.status,
            'created_at': order.created_at
        } for order in orders]
    
    return render_template('master/user_report.html', 
                         cafe=cafe, 
                         user=user_data, 
                         action_logs=logs_data,
                         orders=orders_data,
                         total_orders=total_orders,
                         total_actions=total_actions,
                         login_times=login_times)


@master_bp.route('/cafes/<slug>/toggle-active', methods=['POST'])
@master_login_required
def toggle_cafe_active(slug):
    """غیرفعال/فعال کردن کافه"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    cafe.is_active = not cafe.is_active
    db.session.commit()
    
    status = 'فعال' if cafe.is_active else 'غیرفعال'
    flash(f'کافه «{cafe.name}» {status} شد.', 'success')
    
    return redirect(url_for('master.dashboard'))


@master_bp.route('/cafes/<slug>/report')
@master_login_required
def cafe_report(slug):
    """گزارش تفصیلی یک کافه"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    stats = {
        'cafe': cafe,
        'orders_count': 0,
        'revenue': 0,
        'paid_revenue': 0,
        'unpaid_revenue': 0,
        'users_count': 0,
        'menu_items_count': 0,
        'categories_count': 0,
        'customers_count': 0,
        'tables_count': 0,
        'table_areas_count': 0,
        'raw_materials_count': 0,
        'warehouses_count': 0,
        'has_data': False,
        'error': None
    }
    
    if os.path.exists(cafe.db_path):
        try:
            engine = create_engine(f"sqlite:///{cafe.db_path}")
            Session = sessionmaker(bind=engine)
            with Session() as s:
                from models.models import (
                    Order, User, MenuItem, Category, Customer, Table, TableArea,
                    RawMaterial, Warehouse
                )
                from sqlalchemy import func
                
                stats['orders_count'] = s.query(func.count(Order.id)).scalar() or 0
                stats['revenue'] = s.query(func.coalesce(func.sum(Order.final_amount), 0)).scalar() or 0
                stats['paid_revenue'] = s.query(func.coalesce(func.sum(Order.final_amount), 0)).filter(Order.status == 'پرداخت شده').scalar() or 0
                stats['unpaid_revenue'] = s.query(func.coalesce(func.sum(Order.final_amount), 0)).filter(Order.status == 'پرداخت نشده').scalar() or 0
                stats['users_count'] = s.query(func.count(User.id)).scalar() or 0
                stats['menu_items_count'] = s.query(func.count(MenuItem.id)).scalar() or 0
                stats['categories_count'] = s.query(func.count(Category.id)).scalar() or 0
                stats['customers_count'] = s.query(func.count(Customer.id)).scalar() or 0
                stats['tables_count'] = s.query(func.count(Table.id)).scalar() or 0
                stats['table_areas_count'] = s.query(func.count(TableArea.id)).scalar() or 0
                stats['raw_materials_count'] = s.query(func.count(RawMaterial.id)).scalar() or 0
                stats['warehouses_count'] = s.query(func.count(Warehouse.id)).scalar() or 0
                stats['has_data'] = True
                
                # Get recent orders
                recent_orders = s.query(Order).order_by(Order.created_at.desc()).limit(10).all()
                stats['recent_orders'] = [
                    {
                        'id': o.id,
                        'invoice_number': str(o.invoice_number) if o.invoice_number else '-',
                        'final_amount': o.final_amount or 0,
                        'status': o.status,
                        'created_at': o.created_at
                    } for o in recent_orders
                ]
                
                # Get active users
                active_users = s.query(User).filter(User.is_active == True).all()
                stats['active_users'] = [
                    {
                        'id': u.id,
                        'username': u.username,
                        'name': u.name,
                        'role': u.role
                    } for u in active_users
                ]
                
        except Exception as e:
            stats['error'] = str(e)
            stats['has_data'] = False
    
    return render_template('master/cafe_report.html', stats=stats)


@master_bp.route('/user-requests')
@master_login_required
def user_requests():
    """نمایش درخواست‌های ایجاد کاربر (صفحه جداگانه - برای backward compatibility)"""
    requests = UserCreationRequest.query.order_by(UserCreationRequest.created_at.desc()).all()
    
    # Get cafe names for each request
    for req in requests:
        req.cafe = CafeTenant.query.get(req.cafe_id)
    
    return render_template('master/user_requests.html', requests=requests)


@master_bp.route('/user-requests/<int:request_id>/approve', methods=['POST'])
@master_login_required
def approve_user_request(request_id):
    """تایید درخواست ایجاد کاربر و ساخت کاربر"""
    from werkzeug.security import generate_password_hash
    import secrets
    import string
    
    req = UserCreationRequest.query.get_or_404(request_id)
    
    if req.status != 'pending':
        flash('این درخواست قبلاً پردازش شده است.', 'warning')
        return redirect(url_for('master.dashboard') + '#requests')
    
    cafe = CafeTenant.query.get(req.cafe_id)
    if not cafe or not os.path.exists(cafe.db_path):
        flash('کافه یا دیتابیس یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard') + '#requests')
    
    # Use requested username (the one admin entered, e.g., "sandoq1")
    requested_username = req.username
    if not requested_username:
        # Generate random username if not provided
        requested_username = f"user_{secrets.token_hex(4)}"
    
    # Generate random password (8 characters)
    generated_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    
    # Connect to tenant DB and create user
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    try:
        with Session() as s:
            # Check if there's a temporary user created for this request
            temp_user_id = None
            if req.notes and req.notes.startswith('temp_user_id:'):
                try:
                    temp_user_id = int(req.notes.split(':')[1])
                except (ValueError, IndexError):
                    temp_user_id = None
            
            # Check if requested username already exists (excluding temp user)
            final_username = requested_username
            existing = s.query(TenantUser).filter_by(username=final_username).first()
            if existing and (not temp_user_id or existing.id != temp_user_id):
                # Username exists, append number to make it unique
                counter = 1
                while s.query(TenantUser).filter_by(username=f"{final_username}{counter}").first():
                    counter += 1
                final_username = f"{final_username}{counter}"
            
            if temp_user_id:
                # Update existing temporary user
                user = s.query(TenantUser).get(temp_user_id)
                if user:
                    user.username = final_username  # Use requested username, not generated one
                    user.password_hash = generate_password_hash(generated_password)
                    user.is_active = True  # Activate the user
                    # Also update name and phone if they were provided in request
                    if req.name:
                        user.name = req.name
                    if req.phone:
                        user.phone = req.phone
                    s.commit()
                else:
                    # Temp user not found, create new one
                    user = TenantUser(
                        username=final_username,
                        password_hash=generate_password_hash(generated_password),
                        name=req.name,
                        role=req.role,
                        phone=req.phone,
                        created_at=datetime.now(pytz.timezone("Asia/Tehran")),
                        is_active=True
                    )
                    s.add(user)
                    s.commit()
            else:
                # No temp user, create new one
                user = TenantUser(
                    username=final_username,
                    password_hash=generate_password_hash(generated_password),
                    name=req.name,
                    role=req.role,
                    phone=req.phone,
                    created_at=datetime.now(pytz.timezone("Asia/Tehran")),
                    is_active=True
                )
                s.add(user)
                s.commit()
        
        # Update request in master database
        # Ensure we're using master database for this update
        from config import Config
        original_bind = db.session.bind
        try:
            # Switch to master database
            master_engine = create_engine(Config.MASTER_DB_URI)
            db.session.bind = master_engine
            
            # Re-query req from master database to ensure we have the latest version
            req = UserCreationRequest.query.get(request_id)
            if not req:
                flash('درخواست یافت نشد.', 'danger')
                return redirect(url_for('master.dashboard') + '#requests')
            
            master_user = _master_user()
            req.status = 'approved'
            req.generated_username = final_username  # Use final_username instead of generated_username
            req.generated_password = generated_password
            req.approved_by = master_user.id if master_user else None
            req.approved_at = datetime.utcnow()
            db.session.commit()
        finally:
            # Restore original bind
            db.session.bind = original_bind
        
        flash(f'کاربر با موفقیت ایجاد شد. نام کاربری: {final_username}, رمز عبور: {generated_password}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'خطا در ایجاد کاربر: {str(e)}', 'danger')
    
    return redirect(url_for('master.dashboard') + '#requests')


@master_bp.route('/user-requests/<int:request_id>/reject', methods=['POST'])
@master_login_required
def reject_user_request(request_id):
    """رد درخواست ایجاد کاربر"""
    req = UserCreationRequest.query.get_or_404(request_id)
    
    if req.status != 'pending':
        flash('این درخواست قبلاً پردازش شده است.', 'warning')
        return redirect(url_for('master.dashboard') + '#requests')
    
    # Delete temporary user if exists
    # First, save the original notes to extract temp_user_id
    original_notes = req.notes or ''
    temp_user_id = None
    if original_notes and original_notes.startswith('temp_user_id:'):
        try:
            temp_user_id = int(original_notes.split(':')[1])
        except (ValueError, IndexError):
            temp_user_id = None
    
    if temp_user_id:
        cafe = CafeTenant.query.get(req.cafe_id)
        if cafe and os.path.exists(cafe.db_path):
            # Connect to tenant DB and delete temp user
            engine = create_engine(f"sqlite:///{cafe.db_path}")
            Session = sessionmaker(bind=engine)
            try:
                with Session() as s:
                    temp_user = s.query(TenantUser).get(temp_user_id)
                    if temp_user:
                        s.delete(temp_user)
                        s.commit()
                        print(f"✅ Temp user {temp_user_id} deleted successfully")
                    else:
                        print(f"⚠️  Temp user {temp_user_id} not found in tenant DB")
            except Exception as e:
                current_app.logger.error(f"Error deleting temp user for request {request_id}: {e}", exc_info=True)
                print(f"❌ Error deleting temp user: {e}")
    
    # Update request status
    # Preserve original notes if it contains temp_user_id, otherwise use form notes
    req.status = 'rejected'
    rejection_notes = request.form.get('notes', '').strip()
    if rejection_notes:
        # If user provided rejection notes, append to original notes
        if original_notes and original_notes.startswith('temp_user_id:'):
            req.notes = f"{original_notes}; rejection_reason: {rejection_notes}"
        else:
            req.notes = rejection_notes
    else:
        # Keep original notes if no rejection reason provided
        req.notes = original_notes
    
    # Ensure we're using master database for commit
    from config import Config
    original_bind = db.session.bind
    try:
        master_engine = create_engine(Config.MASTER_DB_URI)
        db.session.bind = master_engine
        db.session.commit()
    finally:
        db.session.bind = original_bind
    
    flash('درخواست رد شد و کاربر موقت حذف شد.', 'info')
    return redirect(url_for('master.dashboard') + '#requests')


@master_bp.route('/cafes/<slug>/delete', methods=['POST'])
@master_login_required
def delete_cafe(slug):
    """حذف کامل کافه و تمام داده‌هایش"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    cafe_name = cafe.name
    
    try:
        # Delete all CafeModule records
        CafeModule.query.filter_by(cafe_id=cafe.id).delete()
        
        # Delete cafe from master DB
        db.session.delete(cafe)
        db.session.commit()
        
        # Delete tenant directory and database
        import shutil
        if os.path.exists(cafe.root_dir):
            shutil.rmtree(cafe.root_dir, ignore_errors=True)
        
        flash(f'کافه «{cafe_name}» و تمام داده‌هایش حذف شد.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'خطا در حذف کافه: {e}', 'danger')
    
    return redirect(url_for('master.dashboard'))


@master_bp.route('/user-requests/<int:request_id>/delete-user', methods=['POST'])
@master_login_required
def delete_user(request_id):
    """حذف کاربر از دیتابیس کافه"""
    req = UserCreationRequest.query.get_or_404(request_id)
    
    if req.status != 'approved' or not req.generated_username:
        flash('این درخواست تایید نشده یا کاربری ایجاد نشده است.', 'warning')
        return redirect(url_for('master.dashboard') + '#requests')
    
    cafe = CafeTenant.query.get(req.cafe_id)
    if not cafe or not os.path.exists(cafe.db_path):
        flash('کافه یا دیتابیس یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard') + '#requests')
    
    # Connect to tenant DB and delete user
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    user_deleted = False
    try:
        with Session() as s:
            user = s.query(TenantUser).filter_by(username=req.generated_username).first()
            if user:
                s.delete(user)
                s.commit()
                user_deleted = True
                flash(f'کاربر «{req.generated_username}» از دیتابیس حذف شد.', 'success')
            else:
                flash('کاربر در دیتابیس یافت نشد.', 'warning')
        
        # تغییر وضعیت درخواست به deleted فقط اگر کاربر حذف شد
        if user_deleted:
            from config import Config
            original_bind = db.session.bind
            try:
                master_engine = create_engine(Config.MASTER_DB_URI)
                db.session.bind = master_engine
                req = UserCreationRequest.query.get(request_id)
                if req:
                    req.status = 'deleted'
                    req.generated_username = None  # حذف نام کاربری از نمایش
                    req.generated_password = None  # حذف رمز عبور از نمایش
                    db.session.commit()
            finally:
                db.session.bind = original_bind
    except Exception as e:
        current_app.logger.error(f"Error deleting user for request {request_id}: {e}", exc_info=True)
        flash(f'خطا در حذف کاربر: {str(e)}', 'danger')
    
    return redirect(url_for('master.dashboard') + '#requests')


@master_bp.route('/user-requests/<int:request_id>/deactivate-user', methods=['POST'])
@master_login_required
def deactivate_user(request_id):
    """غیرفعال کردن کاربر و حذف رمز عبور"""
    from werkzeug.security import generate_password_hash
    import secrets
    import string
    
    req = UserCreationRequest.query.get_or_404(request_id)
    
    if req.status != 'approved' or not req.generated_username:
        flash('این درخواست تایید نشده یا کاربری ایجاد نشده است.', 'warning')
        return redirect(url_for('master.dashboard') + '#requests')
    
    cafe = CafeTenant.query.get(req.cafe_id)
    if not cafe or not os.path.exists(cafe.db_path):
        flash('کافه یا دیتابیس یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard') + '#requests')
    
    # Connect to tenant DB and deactivate user
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    try:
        with Session() as s:
            user = s.query(TenantUser).filter_by(username=req.generated_username).first()
            if user:
                # غیرفعال کردن کاربر و حذف رمز عبور (با قرار دادن یک رمز عبور غیرقابل استفاده)
                user.is_active = False
                # ایجاد یک رمز عبور تصادفی طولانی که کاربر نمی‌تواند آن را حدس بزند
                random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
                user.password_hash = generate_password_hash(random_password)
                s.commit()
                
                # حذف رمز عبور از درخواست
                from config import Config
                original_bind = db.session.bind
                try:
                    master_engine = create_engine(Config.MASTER_DB_URI)
                    db.session.bind = master_engine
                    req = UserCreationRequest.query.get(request_id)
                    if req:
                        req.generated_password = None  # حذف رمز عبور از درخواست
                        db.session.commit()
                finally:
                    db.session.bind = original_bind
                
                flash(f'کاربر «{req.generated_username}» غیرفعال شد و رمز عبور حذف شد.', 'success')
            else:
                flash('کاربر در دیتابیس یافت نشد.', 'warning')
    except Exception as e:
        current_app.logger.error(f"Error deactivating user for request {request_id}: {e}", exc_info=True)
        flash(f'خطا در غیرفعال کردن کاربر: {str(e)}', 'danger')
    
    return redirect(url_for('master.dashboard') + '#requests')


@master_bp.route('/user-requests/<int:request_id>/reactivate-user', methods=['POST'])
@master_login_required
def reactivate_user(request_id):
    """فعال کردن مجدد کاربر با رمز عبور جدید"""
    from werkzeug.security import generate_password_hash
    import secrets
    import string
    
    req = UserCreationRequest.query.get_or_404(request_id)
    
    if req.status != 'approved' or not req.generated_username:
        flash('این درخواست تایید نشده یا کاربری ایجاد نشده است.', 'warning')
        return redirect(url_for('master.dashboard') + '#requests')
    
    cafe = CafeTenant.query.get(req.cafe_id)
    if not cafe or not os.path.exists(cafe.db_path):
        flash('کافه یا دیتابیس یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard') + '#requests')
    
    # Generate new password
    new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    
    # Connect to tenant DB and reactivate user
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    try:
        with Session() as s:
            user = s.query(TenantUser).filter_by(username=req.generated_username).first()
            if user:
                # فعال کردن کاربر و تنظیم رمز عبور جدید
                user.is_active = True
                user.password_hash = generate_password_hash(new_password)
                s.commit()
                
                # به‌روزرسانی رمز عبور در درخواست
                from config import Config
                original_bind = db.session.bind
                try:
                    master_engine = create_engine(Config.MASTER_DB_URI)
                    db.session.bind = master_engine
                    req = UserCreationRequest.query.get(request_id)
                    if req:
                        req.generated_password = new_password
                        db.session.commit()
                finally:
                    db.session.bind = original_bind
                
                flash(f'کاربر «{req.generated_username}» فعال شد. رمز عبور جدید: {new_password}', 'success')
            else:
                flash('کاربر در دیتابیس یافت نشد.', 'warning')
    except Exception as e:
        current_app.logger.error(f"Error reactivating user for request {request_id}: {e}", exc_info=True)
        flash(f'خطا در فعال کردن کاربر: {str(e)}', 'danger')
    
    return redirect(url_for('master.dashboard') + '#requests')


@master_bp.route('/user-requests/<int:request_id>/delete-request', methods=['POST'])
@master_login_required
def delete_request(request_id):
    """حذف کامل درخواست از master database"""
    try:
        # حذف درخواست از master database
        from config import Config
        original_bind = db.session.bind
        try:
            master_engine = create_engine(Config.MASTER_DB_URI)
            db.session.bind = master_engine
            
            # پیدا کردن درخواست
            req = UserCreationRequest.query.get(request_id)
            if not req:
                flash('درخواست یافت نشد.', 'warning')
                return redirect(url_for('master.dashboard') + '#requests')
            
            # حذف کامل از دیتابیس
            db.session.delete(req)
            db.session.commit()
            
            flash('درخواست به طور کامل از دیتابیس حذف شد.', 'success')
        finally:
            db.session.bind = original_bind
    except Exception as e:
        current_app.logger.error(f"Error deleting request {request_id}: {e}", exc_info=True)
        flash(f'خطا در حذف درخواست: {str(e)}', 'danger')
    
    return redirect(url_for('master.dashboard') + '#requests')


@master_bp.route('/user-requests/delete-all', methods=['POST'])
@master_login_required
def delete_all_requests():
    """حذف کامل تمام درخواست‌ها از master database"""
    try:
        from config import Config
        original_bind = db.session.bind
        try:
            master_engine = create_engine(Config.MASTER_DB_URI)
            db.session.bind = master_engine
            
            # شمارش درخواست‌ها قبل از حذف
            count_before = UserCreationRequest.query.count()
            
            # حذف تمام درخواست‌ها
            UserCreationRequest.query.delete()
            db.session.commit()
            
            flash(f'تمام {count_before} درخواست به طور کامل از دیتابیس حذف شدند.', 'success')
        finally:
            db.session.bind = original_bind
    except Exception as e:
        current_app.logger.error(f"Error deleting all requests: {e}", exc_info=True)
        flash(f'خطا در حذف درخواست‌ها: {str(e)}', 'danger')
    
    return redirect(url_for('master.dashboard') + '#requests')