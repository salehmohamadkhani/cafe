from __future__ import annotations

from datetime import datetime

import os
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from models.models import db
from models.master_models import CafeTenant, MasterUser
from services.tenant_provisioning import provision_tenant
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import User as TenantUser

master_bp = Blueprint('master', __name__, url_prefix='/master')


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
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if not username or not password:
            flash('نام کاربری و رمز عبور الزامی است.', 'danger')
            return render_template('master/login.html')

        user = MasterUser.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
            return render_template('master/login.html')

        if not user.is_active:
            flash('این حساب غیرفعال است.', 'danger')
            return render_template('master/login.html')

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
    return render_template('master/dashboard.html', master_user=user, cafes=cafes)


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
    
    # Get default admin user from tenant DB
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    
    admin_user = None
    with Session() as s:
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

