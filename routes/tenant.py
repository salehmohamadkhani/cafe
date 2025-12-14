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
    """Redirect to tenant's own dashboard"""
    return redirect(url_for('tenant.dashboard_full', slug=slug))


@tenant_bp.route('/dashboard/')
@tenant_bp.route('/dashboard')
@require_tenant_session
def dashboard_full(slug):
    """داشبورد کامل کافه - مثل پروژه اصلی"""
    Session_class, cafe = get_tenant_db_session(slug)
    if not Session_class:
        flash('خطا در اتصال به دیتابیس کافه.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    # Import models from tenant's own project
    from models.models import Order, Category, MenuItem, Customer, Table
    from datetime import datetime, timedelta, date
    from sqlalchemy import func
    from collections import defaultdict
    
    with Session_class() as s:
        # Get all menu items
        menu_items = s.query(MenuItem).filter_by(is_active=True).order_by(MenuItem.name).all()
        
        # Get all categories
        categories = s.query(Category).filter_by(is_active=True).order_by(Category.order, Category.name).all()
        
        # Get all customers
        customers = s.query(Customer).all()
        
        # Get all tables, create default if none exist
        tables = s.query(Table).order_by(Table.number).all()
        if not tables:
            for i in range(1, 5):
                table = Table(number=i, status='خالی')
                s.add(table)
            s.commit()
            tables = s.query(Table).order_by(Table.number).all()
        
        # Group tables by area
        table_groups_map = defaultdict(list)
        for table in tables:
            label = table.area.name if hasattr(table, 'area') and table.area else 'بدون دسته‌بندی'
            table_groups_map[label].append(table)
        
        table_groups = []
        for label in sorted(table_groups_map.keys()):
            ordered_tables = sorted(table_groups_map[label], key=lambda t: t.number)
            table_groups.append({'label': label, 'tables': ordered_tables})
        
        # Calculate financial info
        import pytz
        iran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(iran_tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Today's orders
        orders_today = s.query(Order).filter(Order.created_at >= today_start).all()
        total_sales_today = sum(o.final_amount for o in orders_today if o.status == 'پرداخت شده')
        unpaid_amount = sum(o.final_amount for o in orders_today if o.status == 'پرداخت نشده')
        
        # Recent orders
        recent_orders = s.query(Order).order_by(Order.created_at.desc()).limit(10).all()
    
    # Render tenant's own dashboard template (which should be a copy of main dashboard)
    return render_template('dashboard.html', 
                         menu_items=menu_items,
                         categories=categories,
                         customers=customers,
                         table_groups=table_groups,
                         total_sales_today=total_sales_today,
                         unpaid_amount=unpaid_amount,
                         recent_orders=recent_orders)
