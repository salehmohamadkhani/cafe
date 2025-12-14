from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.models import Order, Category, MenuItem, Customer, Table, db
from flask_login import login_required
from sqlalchemy import text, func, extract
from datetime import datetime, timedelta
from collections import defaultdict
import pytz
import jdatetime
from utils.helpers import categorize_payment_method, PAYMENT_BUCKET_LABELS

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def dashboard():
    # Get all menu items
    menu_items = MenuItem.query.filter_by(is_active=True).order_by(MenuItem.name).all()
    
    # Get all categories for menu grouping
    categories = Category.query.filter_by(is_active=True).order_by(Category.order, Category.name).all()
    
    # Get all customers for the datalist
    customers = Customer.query.all()
    
    # Get all tables, if no tables exist, create 4 default tables
    tables = Table.query.order_by(Table.number).all()
    if not tables:
        for i in range(1, 5):
            table = Table(number=i, status='خالی')
            db.session.add(table)
        db.session.commit()
        tables = Table.query.order_by(Table.number).all()

    table_groups_map = defaultdict(list)
    for table in tables:
        label = table.area.name if table.area else 'بدون دسته‌بندی'
        table_groups_map[label].append(table)

    table_groups = []
    for label in sorted(table_groups_map.keys()):
        ordered_tables = sorted(table_groups_map[label], key=lambda t: t.number)
        table_groups.append({'label': label, 'tables': ordered_tables})
    
    # دیگر نیازی به table_orders نیست چون فقط سفارش فعلی (order_id) را نمایش می‌دهیم
    
    # محاسبه اطلاعات مالی
    iran_tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(iran_tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # محاسبه شروع ماه شمسی جاری
    # تبدیل به naive datetime برای jdatetime (SQLite معمولاً naive datetime ذخیره می‌کند)
    now_naive = now.replace(tzinfo=None) if now.tzinfo else now
    jalali_now = jdatetime.datetime.fromgregorian(datetime=now_naive)
    jalali_month_start = jdatetime.datetime(jalali_now.year, jalali_now.month, 1, 0, 0, 0)
    # تبدیل به میلادی برای فیلتر کردن در دیتابیس (به صورت naive چون SQLite naive ذخیره می‌کند)
    month_start_naive = jalali_month_start.togregorian().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # محاسبه پایان ماه شمسی جاری
    if jalali_now.month == 12:
        # آخرین ماه سال - 29 یا 30 روز بسته به سال کبیسه
        last_day = 29 if jdatetime.date.isleap(jalali_now.year) else 30
    elif jalali_now.month <= 6:
        last_day = 31
    else:
        last_day = 30
    jalali_month_end = jdatetime.datetime(jalali_now.year, jalali_now.month, last_day, 23, 59, 59)
    month_end_naive = jalali_month_end.togregorian().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # دیباگ: چاپ تاریخ‌های محاسبه شده
    print(f"🔍 دیباگ تاریخ شمسی: ماه {jalali_now.month} سال {jalali_now.year}")
    print(f"🔍 شروع ماه میلادی: {month_start_naive}")
    print(f"🔍 پایان ماه میلادی: {month_end_naive}")
    
    def summarize_period(key, label, start_dt, end_dt=None):
        query = Order.query.filter(Order.created_at >= start_dt)
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
    
    # استفاده از دوره ماه جاری برای مقادیر پیش‌فرض قدیمی
    month_orders_count = active_period['orders_count']
    month_paid_count = active_period['paid_count']
    month_revenue = active_period['total_sales']
    month_paid_revenue = active_period['paid_total']
    today_orders_count = periods[0]['orders_count']
    today_paid_count = periods[0]['paid_count']
    today_revenue = periods[0]['paid_total']
    
    # سفارشات پرداخت نشده
    unpaid_count = db.session.query(func.count(Order.id)).filter(Order.status == 'پرداخت نشده').scalar() or 0
    unpaid_total = db.session.query(func.coalesce(func.sum(Order.final_amount), 0)).filter(Order.status == 'پرداخت نشده').scalar() or 0
    unpaid_orders = Order.query.filter(Order.status == 'پرداخت نشده').order_by(Order.created_at.desc()).limit(10).all()
    
    # آخرین سفارشات
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # آمار پرداخت‌ها (فقط پرداخت شده‌ها)
    payment_stats = active_period['payment']
    
    # آمار نوع سفارش
    order_type_stats = active_period['order_types']
    
    # مالیات و تخفیف این ماه
    month_tax = active_period['tax_total']
    month_discount = active_period['discount_total']
    
    financial_data = {
        'today_revenue': today_revenue,
        'today_orders_count': today_orders_count,
        'today_paid_count': today_paid_count,
        'month_revenue': month_revenue,  # کل فروش ماه (شامل پرداخت نشده‌ها)
        'month_paid_revenue': month_paid_revenue,  # فقط پرداخت شده‌ها
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
    
    # دریافت سفارشات بیرون‌بر پرداخت نشده
    takeaway_orders = Order.query.filter(
        Order.type == 'بیرون‌بر',
        Order.status == 'پرداخت نشده'
    ).order_by(Order.created_at.desc()).all()
    
    # دیگر نیازی به table_orders نیست چون فقط سفارش فعلی را نمایش می‌دهیم
    # table_orders = {}  # حذف شده - دیگر استفاده نمی‌شود
    
    return render_template('dashboard.html', 
                          orders=Order.query.all(),
                          menu_items=menu_items,
                          categories=categories,
                          customers=customers,
                          tables=tables,
                          table_groups=table_groups,
                          financial=financial_data,
                          takeaway_orders=takeaway_orders)

# --- تغییر دسته‌ای وضعیت سفارش‌های پرداخت نشده به پرداخت شده ---
@dashboard_bp.route('/mark-all-unpaid-as-paid', methods=['POST'])
@login_required
def mark_all_unpaid_as_paid():
    """تغییر وضعیت تمام سفارش‌های پرداخت نشده به پرداخت شده"""
    try:
        iran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(iran_tz)
        
        # پیدا کردن تمام سفارش‌های پرداخت نشده
        unpaid_orders = Order.query.filter(Order.status == 'پرداخت نشده').all()
        
        count = 0
        total_amount = 0
        
        for order in unpaid_orders:
            order.status = 'پرداخت شده'
            if not order.paid_at:
                order.paid_at = now
            if not order.payment_method:
                order.payment_method = 'کارتخوان'  # پیش‌فرض کارتخوان
            count += 1
            total_amount += order.final_amount
        
        db.session.commit()
        
        flash(f'✅ {count} سفارش با مجموع {total_amount:,} به وضعیت "پرداخت شده" تغییر یافت.', 'success')
        print(f"✅ {count} سفارش پرداخت نشده به پرداخت شده تغییر یافت. مجموع: {total_amount:,}")
        
        return redirect(url_for('dashboard.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ خطا در تغییر وضعیت سفارش‌ها: {str(e)}', 'danger')
        print(f"❌ خطا: {str(e)}")
        return redirect(url_for('dashboard.dashboard'))
