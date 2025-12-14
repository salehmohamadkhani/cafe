from __future__ import annotations

import os
from flask import Blueprint, render_template, redirect, url_for, session, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.master_models import CafeTenant
from models.models import Order, Customer

tenant_bp = Blueprint('tenant', __name__, url_prefix='/cafe/<slug>')


def require_tenant_session(view_func):
    """Decorator to ensure user is logged into a tenant"""
    def wrapper(slug, *args, **kwargs):
        if session.get('tenant_slug') != slug:
            flash('لطفاً ابتدا وارد کافه شوید.', 'warning')
            return redirect(url_for('tenant_auth.login', slug=slug))
        return view_func(slug, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


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


@tenant_bp.route('/')
@require_tenant_session
def dashboard(slug):
    """داشبورد کافه"""
    Session, cafe = get_tenant_db_session(slug)
    if not Session:
        flash('خطا در اتصال به دیتابیس کافه.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    from datetime import datetime, date
    from sqlalchemy import func
    
    with Session() as s:
        today = date.today()
        orders_today = s.query(Order).filter(func.date(Order.created_at) == today).all()
        total_orders = len(orders_today)
        total_sales = sum(o.final_amount for o in orders_today)
        unpaid_orders = [o for o in orders_today if o.status == 'پرداخت نشده']
        paid_orders = [o for o in orders_today if o.status == 'پرداخت شده']
        
        summary = {
            'total_orders': total_orders,
            'total_sales': total_sales,
            'unpaid_orders': len(unpaid_orders),
            'paid_orders': len(paid_orders),
        }
        
        recent_orders = s.query(Order).order_by(Order.created_at.desc()).limit(20).all()
    
    return render_template('tenant/dashboard.html', cafe=cafe, summary=summary, orders=recent_orders)
