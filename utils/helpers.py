import locale
import jdatetime
import os
from datetime import datetime
from typing import Optional, ContextManager
from contextlib import contextmanager
from flask import session, current_app
from sqlalchemy import create_engine
from models.master_models import CafeTenant
from models.models import db

locale.setlocale(locale.LC_ALL, '')

PAYMENT_BUCKET_LABELS = {
    'pos': 'کارتخوان',
    'card_to_card': 'کارت به کارت',
    'snap': 'اسنپ'
}

PAYMENT_BUCKET_KEYWORDS = {
    'pos': {'نقدی', 'کارتخوان', 'کارت', 'پوز', 'pos', 'cash'},
    'card_to_card': {'کارت به کارت', 'انتقال', 'واریز', 'حواله', 'transfer', 'آنلاین', 'online', 'internet'},
    'snap': {'اسنپ', 'snap', 'snapp', 'اسنپ', 'اسنپ'}
}

def format_price(price):
    """Format price as a string with thousands separator and currency."""
    try:
        price = float(price)
    except (ValueError, TypeError):
        return "نامعتبر"
    return f"{price:,.0f}"

def format_datetime(dt, fmt='%Y/%m/%d %H:%M'):
    """Format a datetime object to Persian-friendly string."""
    if not dt:
        return ''
    return dt.strftime(fmt)

def format_number(num, decimals=0):
    """Format a number with thousands separator and optional decimals."""
    try:
        num = float(num)
    except (ValueError, TypeError):
        return "نامعتبر"
    if decimals > 0:
        return f"{num:,.{decimals}f}"
    return f"{num:,.0f}"

def percent(value, total):
    """Return percent string of value over total."""
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return "۰٪"
        return f"{(value / total) * 100:.1f}%"
    except (ValueError, TypeError, ZeroDivisionError):
        return "۰٪"

def to_iranian_digits(s):
    """Convert English digits in a string to Persian digits."""
    if not isinstance(s, str):
        s = str(s)
    en = '0123456789'
    fa = '۰۱۲۳۴۵۶۷۸۹'
    for e, f in zip(en, fa):
        s = s.replace(e, f)
    return s


def categorize_payment_method(method: Optional[str]) -> str:
    """Map various free-text payment methods to the limited dashboard buckets."""
    normalized = (method or '').strip().lower()
    if not normalized:
        return 'pos'
    for bucket, keywords in PAYMENT_BUCKET_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return bucket
    return 'pos'

def currency_to_number(s):
    """Convert a formatted currency string to a float."""
    if not s:
        return 0
    s = str(s).replace('تومان', '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return 0

def format_order_status(status):
    """Return a styled HTML badge for order status."""
    status = str(status)
    if status == 'پرداخت شده':
        return '<span class="badge bg-success">پرداخت شده</span>'
    elif status == 'پرداخت نشده':
        return '<span class="badge bg-warning text-dark">پرداخت نشده</span>'
    elif status == 'لغو شده':
        return '<span class="badge bg-danger">لغو شده</span>'
    else:
        return f'<span class="badge bg-secondary">{status}</span>'

def format_order_type(order_type):
    """Return a styled HTML badge for order type."""
    order_type = str(order_type)
    if order_type == 'حضوری':
        return '<span class="badge bg-primary">حضوری</span>'
    elif order_type == 'بیرون‌بر':
        return '<span class="badge bg-info text-dark">بیرون‌بر</span>'
    else:
        return f'<span class="badge bg-secondary">{order_type}</span>'

def humanize_timesince(dt, now=None):
    """Return a human-readable time difference (e.g., '۲ ساعت پیش')."""
    from datetime import datetime
    if not dt:
        return ''
    now = now or datetime.utcnow()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{to_iranian_digits(seconds)} ثانیه پیش"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{to_iranian_digits(minutes)} دقیقه پیش"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{to_iranian_digits(hours)} ساعت پیش"
    else:
        days = seconds // 86400
        return f"{to_iranian_digits(days)} روز پیش"

def safe_str(s):
    """Return a safe string for display."""
    if s is None:
        return ''
    return str(s).replace('<', '<').replace('>', '>')

# Jinja2 filters registration (if used in Flask app)
def to_jalali(value, format='%Y/%m/%d %H:%M'):
    if not value:
        return ''
    try:
        jd = jdatetime.datetime.fromgregorian(date=value)
        return jd.strftime(format)
    except Exception:
        return ''


def parse_jalali_date(date_str: Optional[str]):
    """Convert Jalali date string (e.g., 14/3/1404) to Gregorian date."""
    if not date_str:
        return datetime.now().date()
    normalized = str(date_str).strip().replace('-', '/').replace('.', '/')
    try:
        jd = jdatetime.datetime.strptime(normalized, '%d/%m/%Y')
    except ValueError:
        try:
            jd = jdatetime.datetime.strptime(normalized, '%Y/%m/%d')
        except ValueError:
            return datetime.now().date()
    return jd.togregorian().date()

def register_jinja_filters(app):
    app.jinja_env.filters['price'] = format_price
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['number'] = format_number
    app.jinja_env.filters['iran_digits'] = to_iranian_digits
    app.jinja_env.filters['order_status'] = format_order_status
    app.jinja_env.filters['order_type'] = format_order_type
    app.jinja_env.filters['timesince'] = humanize_timesince
    app.jinja_env.filters['safe_str'] = safe_str
    app.jinja_env.filters['to_jalali'] = to_jalali
    
    # اضافه کردن تابع now به عنوان global function
    # استفاده از lambda برای اینکه هر بار datetime.now() صدا زده شود
    app.jinja_env.globals['now'] = lambda: datetime.now()
    
    # اضافه کردن تابع cache_bust برای جلوگیری از cache مرورگر
    import time
    app.jinja_env.globals['cache_bust'] = lambda: int(time.time())


@contextmanager
def tenant_db_context(slug: Optional[str] = None):
    """
    Context manager to switch db.session to tenant database.
    Usage:
        with tenant_db_context(slug):
            orders = Order.query.all()  # Uses tenant database
    """
    if not slug:
        slug = session.get('tenant_slug')
    
    if not slug:
        # No tenant context, use default database
        yield
        return
    
    # Get tenant database path
    with current_app.app_context():
        cafe = CafeTenant.query.filter_by(slug=slug).first()
    
    if not cafe or not os.path.exists(cafe.db_path):
        # Tenant not found or database doesn't exist, use default
        yield
        return
    
    # Create engine for tenant database
    tenant_engine = create_engine(f"sqlite:///{cafe.db_path}")
    
    # Store original bind
    original_bind = db.session.bind
    
    try:
        # Switch to tenant database
        db.session.bind = tenant_engine
        yield
    finally:
        # Restore original bind
        db.session.bind = original_bind


def get_tenant_slug() -> Optional[str]:
    """Get current tenant slug from session."""
    return session.get('tenant_slug')


def use_tenant_db(view_func):
    """
    Decorator to automatically use tenant database for a route.
    The route must have 'slug' parameter (from URL or session).
    Usage:
        @bp.route('/cafe/<slug>/orders')
        @use_tenant_db
        def orders(slug):
            orders = Order.query.all()  # Uses tenant database
    """
    from functools import wraps
    
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # Try to get slug from kwargs (route parameter) or session
        slug = kwargs.get('slug') or session.get('tenant_slug')
        
        if slug:
            with tenant_db_context(slug):
                return view_func(*args, **kwargs)
        else:
            # No tenant context, use default database
            return view_func(*args, **kwargs)
    
    return wrapper


def restrict_cashier_access(view_func):
    """
    Decorator to restrict cashier role access to specific routes only.
    Cashier can only access:
    - dashboard.dashboard
    - admin.financial_report (only with period=day)
    
    Usage:
        @bp.route('/some-route')
        @restrict_cashier_access
        @login_required
        def some_route():
            ...
    """
    from functools import wraps
    from flask import request, redirect, url_for, flash
    from flask_login import current_user
    
    allowed_routes = ['dashboard.dashboard', 'admin.financial_report']
    
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # Check if user is cashier
        if current_user.is_authenticated and current_user.role == 'cashier':
            # Get current route name
            route_name = request.endpoint
            
            # Check if route is allowed for cashier
            if route_name not in allowed_routes:
                flash('شما دسترسی به این صفحه را ندارید. صندوق‌دار فقط به داشبورد و گزارش‌های امروز دسترسی دارد.', 'danger')
                return redirect(url_for('dashboard.dashboard'))
            
            # For financial_report, only allow period=day
            if route_name == 'admin.financial_report':
                period = request.args.get('period', 'day')
                if period != 'day':
                    flash('صندوق‌دار فقط می‌تواند گزارش امروز را مشاهده کند.', 'warning')
                    return redirect(url_for('admin.financial_report', period='day'))
        
        return view_func(*args, **kwargs)
    
    return wrapper
