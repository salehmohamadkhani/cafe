import locale
import jdatetime
    
locale.setlocale(locale.LC_ALL, '')

def format_price(price):
    """Format price as a string with thousands separator and currency."""
    try:
        price = float(price)
    except (ValueError, TypeError):
        return "نامعتبر"
    return f"{price:,.0f} تومان"

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
        jd = jdatetime.datetime.fromgregorian(datetime=value)
        return jd.strftime(format)
    except Exception:
        return ''

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