from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from models.models import db, User
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import pytz

iran_tz = pytz.timezone("Asia/Tehran")

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Redirect old auth/login to master login"""
    return redirect(url_for('master.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip() or None
        phone = request.form.get('phone', '').strip() or None
        role = request.form.get('role', 'waiter').strip()
        
        # اعتبارسنجی
        errors = []
        
        if not username:
            errors.append('نام کاربری الزامی است.')
        elif len(username) < 3:
            errors.append('نام کاربری باید حداقل ۳ کاراکتر باشد.')
        elif User.query.filter_by(username=username).first():
            errors.append('این نام کاربری قبلاً استفاده شده است.')
        
        if not password:
            errors.append('رمز عبور الزامی است.')
        elif len(password) < 6:
            errors.append('رمز عبور باید حداقل ۶ کاراکتر باشد.')
        elif password != confirm_password:
            errors.append('رمز عبور و تکرار آن یکسان نیستند.')
        
        if phone and User.query.filter_by(phone=phone).first():
            errors.append('این شماره تماس قبلاً استفاده شده است.')
        
        if role not in ['waiter', 'admin']:
            role = 'waiter'
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')
        
        # ایجاد کاربر جدید
        try:
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                name=name,
                phone=phone,
                role=role,
                created_at=datetime.now(iran_tz),
                is_active=True
            )
            db.session.add(new_user)
            db.session.commit()
            flash('ثبت نام با موفقیت انجام شد. اکنون می‌توانید وارد شوید.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('خطا در ثبت نام. لطفاً دوباره تلاش کنید.', 'danger')
            print(f"Error registering user: {e}")
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    """Logout user - handles both tenant and master users"""
    from flask import session
    from flask_login import logout_user
    
    # Get tenant_slug before clearing session
    tenant_slug = session.get('tenant_slug')
    
    # Logout from Flask-Login
    logout_user()
    
    # Clear all session variables
    session.pop('tenant_slug', None)
    session.pop('tenant_db_path', None)
    session.pop('tenant_user_id', None)
    session.pop('tenant_username', None)
    session.pop('master_user_id', None)
    
    # Redirect based on context
    if tenant_slug:
        flash('با موفقیت از کافه خارج شدید.', 'info')
        return redirect(url_for('tenant_auth.login', slug=tenant_slug))
    else:
        flash('با موفقیت خارج شدید.', 'info')
        return redirect(url_for('master.login'))