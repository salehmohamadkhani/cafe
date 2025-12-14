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
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('لطفاً نام کاربری و رمز عبور را وارد کنید.')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('حساب کاربری شما غیرفعال است. لطفاً با مدیر سیستم تماس بگیرید.')
                return render_template('auth/login.html')
            login_user(user)
            user.last_login = datetime.now(iran_tz)
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.dashboard'))
        flash('نام کاربری یا رمز عبور اشتباه است.')
    return render_template('auth/login.html')

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
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))