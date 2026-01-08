from __future__ import annotations

import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import login_user
from werkzeug.security import check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytz

from models.master_models import CafeTenant
from models.models import User

iran_tz = pytz.timezone("Asia/Tehran")

tenant_auth_bp = Blueprint('tenant_auth', __name__, url_prefix='/cafe/<slug>')


def get_tenant_db_session(slug: str):
    """Get a session connected to tenant database"""
    from flask import current_app
    with current_app.app_context():
        cafe = CafeTenant.query.filter_by(slug=slug).first()
    if not cafe or not os.path.exists(cafe.db_path):
        return None, None
    
    engine = create_engine(f"sqlite:///{cafe.db_path}")
    Session = sessionmaker(bind=engine)
    return Session, cafe


@tenant_auth_bp.route('/login', methods=['GET', 'POST'])
def login(slug):
    """لاگین برای یک کافه خاص"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    if not cafe.is_active:
        return render_template('tenant/inactive.html', cafe=cafe), 403
    
    if not os.path.exists(cafe.db_path):
        flash('دیتابیس کافه یافت نشد.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        
        if not username or not password:
            flash('نام کاربری و رمز عبور الزامی است.', 'danger')
            return render_template('tenant/login.html', cafe=cafe)
        
        # Connect to tenant DB
        Session_class, cafe_check = get_tenant_db_session(slug)
        if not Session_class:
            flash('خطا در اتصال به دیتابیس کافه.', 'danger')
            return render_template('tenant/login.html', cafe=cafe)
        
        with Session_class() as s:
            user = s.query(User).filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                if not user.is_active:
                    flash('حساب کاربری شما غیرفعال است.', 'danger')
                    return render_template('tenant/login.html', cafe=cafe)
                
                # Store tenant context in session
                session['tenant_slug'] = slug
                session['tenant_db_path'] = cafe.db_path
                session['tenant_user_id'] = user.id
                session['tenant_username'] = user.username
                
                user.last_login = datetime.now(iran_tz)
                s.commit()
                
                # Also login with Flask-Login so @login_required decorators work
                # We need to reload user from tenant DB after commit
                from flask_login import login_user
                login_user(user, remember=True)
                
                # Redirect to tenant dashboard (or main dashboard for now)
                return redirect(url_for('tenant.dashboard', slug=slug))
            else:
                flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
    
    return render_template('tenant/login.html', cafe=cafe)


@tenant_auth_bp.route('/logout')
def logout(slug):
    """خروج از کافه"""
    from flask_login import logout_user
    logout_user()  # Logout from Flask-Login
    session.pop('tenant_slug', None)
    session.pop('tenant_db_path', None)
    session.pop('tenant_user_id', None)
    session.pop('tenant_username', None)
    flash('با موفقیت از کافه خارج شدید.', 'info')
    return redirect(url_for('tenant_auth.login', slug=slug))
