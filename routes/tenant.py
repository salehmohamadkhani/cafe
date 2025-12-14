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
    """داشبورد کامل کافه - مثل پروژه اصلی - استفاده از پروژه خود کافه"""
    Session_class, cafe = get_tenant_db_session(slug)
    if not Session_class:
        flash('خطا در اتصال به دیتابیس کافه.', 'danger')
        return redirect(url_for('master.dashboard'))
    
    # Import everything needed (same as main dashboard route)
    from models.models import Order, Category, MenuItem, Customer, Table
    from datetime import datetime, timedelta, date
    from sqlalchemy import func
    from collections import defaultdict
    import pytz
    import jdatetime
    from utils.helpers import categorize_payment_method, PAYMENT_BUCKET_LABELS
    
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
            try:
                if hasattr(table, 'area') and table.area:
                    label = table.area.name
                else:
                    label = 'بدون دسته‌بندی'
            except:
                label = 'بدون دسته‌بندی'
            table_groups_map[label].append(table)
        
        table_groups = []
        for label in sorted(table_groups_map.keys()):
            ordered_tables = sorted(table_groups_map[label], key=lambda t: t.number)
            table_groups.append({'label': label, 'tables': ordered_tables})
        
        # Calculate financial info (same as main dashboard)
        iran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(iran_tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate Jalali month start/end
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        jalali_now = jdatetime.datetime.fromgregorian(datetime=now_naive)
        jalali_month_start = jdatetime.datetime(jalali_now.year, jalali_now.month, 1, 0, 0, 0)
        month_start_naive = jalali_month_start.togregorian().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if jalali_now.month == 12:
            last_day = 29 if jdatetime.date.isleap(jalali_now.year) else 30
        elif jalali_now.month <= 6:
            last_day = 31
        else:
            last_day = 30
        jalali_month_end = jdatetime.datetime(jalali_now.year, jalali_now.month, last_day, 23, 59, 59)
        month_end_naive = jalali_month_end.togregorian().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        def summarize_period(key, label, start_dt, end_dt=None):
            query = s.query(Order).filter(Order.created_at >= start_dt)
            if end_dt:
                query = query.filter(Order.created_at <= end_dt)
            orders = query.all()
            
            total_sales = sum(o.final_amount or 0 for o in orders)
            orders_count = len(orders)
            paid_orders = [o for o in orders if o.status == 'پرداخت شده']
            paid_count = len(paid_orders)
            paid_total = sum(o.final_amount or 0 for o in paid_orders)
            unpaid_total = sum(o.final_amount or 0 for o in orders if o.status != 'پرداخت شده')
            payment_stats = {bucket: 0 for bucket in PAYMENT_BUCKET_LABELS.keys()}
            payment_counts = {bucket: 0 for bucket in PAYMENT_BUCKET_LABELS.keys()}
            order_type_stats = {'حضوری': 0, 'بیرون‌بر': 0, 'سایر': 0}
            for order in orders:
                order_type = order.type or 'سایر'
                if order_type not in order_type_stats:
                    order_type_stats[order_type] = 0
                order_type_stats[order_type] += 1
            for order in paid_orders:
                bucket = categorize_payment_method(order.payment_method)
                payment_stats[bucket] += order.final_amount or 0
                payment_counts[bucket] += 1
            tax_total = sum(o.tax_amount or 0 for o in orders)
            discount_total = sum(o.discount or 0 for o in orders)
            
            return {
                'key': key,
                'label': label,
                'total_sales': total_sales,
                'orders_count': orders_count,
                'paid_count': paid_count,
                'paid_total': paid_total,
                'unpaid_total': unpaid_total,
                'payment': payment_stats,
                'payment_counts': payment_counts,
                'tax_total': tax_total,
                'discount_total': discount_total,
                'order_types': order_type_stats
            }
        
        today_start_naive = today_start.replace(tzinfo=None) if today_start.tzinfo else today_start
        periods = [
            summarize_period('day', 'امروز', today_start_naive),
            summarize_period('week', 'هفته جاری (۷ روز)', (today_start_naive - timedelta(days=7))),
            summarize_period('month', 'ماه جاری', month_start_naive, month_end_naive)
        ]
        active_period_key = 'month'
        period_lookup = {p['key']: p for p in periods}
        active_period = period_lookup[active_period_key]
        
        month_orders_count = active_period['orders_count']
        month_paid_count = active_period['paid_count']
        month_revenue = active_period['total_sales']
        month_paid_revenue = active_period['paid_total']
        today_orders_count = periods[0]['orders_count']
        today_paid_count = periods[0]['paid_count']
        today_revenue = periods[0]['paid_total']
        
        unpaid_count = s.query(func.count(Order.id)).filter(Order.status == 'پرداخت نشده').scalar() or 0
        unpaid_total = s.query(func.coalesce(func.sum(Order.final_amount), 0)).filter(Order.status == 'پرداخت نشده').scalar() or 0
        unpaid_orders = s.query(Order).filter(Order.status == 'پرداخت نشده').order_by(Order.created_at.desc()).limit(10).all()
        
        recent_orders = s.query(Order).order_by(Order.created_at.desc()).limit(5).all()
        
        payment_stats = active_period['payment']
        order_type_stats = active_period['order_types']
        month_tax = active_period['tax_total']
        month_discount = active_period['discount_total']
        
        financial_data = {
            'today_revenue': today_revenue,
            'today_orders_count': today_orders_count,
            'today_paid_count': today_paid_count,
            'month_revenue': month_revenue,
            'month_paid_revenue': month_paid_revenue,
            'month_orders_count': month_orders_count,
            'month_paid_count': month_paid_count,
            'unpaid_orders': unpaid_orders,
            'unpaid_total': unpaid_total,
            'unpaid_count': unpaid_count,
            'recent_orders': recent_orders,
            'payment_stats': payment_stats,
            'order_type_stats': order_type_stats,
            'month_tax': month_tax,
            'month_discount': month_discount,
            'periods': periods,
            'active_period': active_period_key
        }
        
        takeaway_orders = s.query(Order).filter(
            Order.type == 'بیرون‌بر',
            Order.status == 'پرداخت نشده'
        ).order_by(Order.created_at.desc()).all()
        
        all_orders = s.query(Order).all()
    
    # Render main dashboard template (same as original project)
    return render_template('dashboard.html', 
                         orders=all_orders,
                         menu_items=menu_items,
                         categories=categories,
                         customers=customers,
                         tables=tables,
                         table_groups=table_groups,
                         financial=financial_data,
                         takeaway_orders=takeaway_orders)
