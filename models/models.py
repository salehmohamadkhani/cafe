from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from flask_login import UserMixin

iran_tz = pytz.timezone("Asia/Tehran")

db = SQLAlchemy()

# --- مدل دسته‌بندی منو ---
class Category(db.Model):
    """دسته‌بندی آیتم‌های منو (مثلاً نوشیدنی‌ها، غذاها و ...)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)  # برای مرتب‌سازی دسته‌بندی‌ها
    created_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    menu_items = db.relationship('MenuItem', backref='category', lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"

# --- مدل آیتم منو ---
class MenuItem(db.Model):
    """آیتم‌های منو (مثلاً قهوه، چای و ...)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)  # قیمت به تومان
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    description = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime)
    stock = db.Column(db.Integer, default=0)

    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)

    def __repr__(self):
        return f"<MenuItem {self.name}>"

# --- مدل مشتری ---
class Customer(db.Model):
    """مشتری (هر مشتری یک id یکتا دارد و می‌تواند چندین سفارش داشته باشد)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    email = db.Column(db.String(128), unique=True, nullable=True)
    address = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime)
    last_visit = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.String(256), nullable=True)  # توضیحات اضافی (مثلاً مشتری ویژه)

    orders = db.relationship('Order', backref='customer', lazy=True)

    def __repr__(self):
        return f"<Customer {self.name} - {self.phone}>"

# --- مدل سفارش ---
class Order(db.Model):
    """سفارش (هر سفارش به یک مشتری متصل است و شامل چند آیتم سفارش است)"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.Integer, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    total_amount = db.Column(db.Integer, nullable=False)
    discount = db.Column(db.Integer, default=0)
    tax_amount = db.Column(db.Integer, default=0)
    final_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), default='پرداخت نشده')  # پرداخت نشده، پرداخت شده، بیرون‌بر، لغو شده و ...
    type = db.Column(db.String(32), default='حضوری')  # حضوری یا بیرون‌بر
    note = db.Column(db.String(256), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    payment_method = db.Column(db.String(32), nullable=True)  # نقدی، کارت، آنلاین و ...
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # اضافه کردن فیلد user_id

    order_items = db.relationship(
    'OrderItem',
    backref='order',
    lazy=True,
    cascade='all, delete-orphan'
    )


    def __repr__(self):
        return f"<Order #{self.invoice_number} - {self.status}>"

# --- مدل آیتم سفارش ---
class OrderItem(db.Model):
    """آیتم‌های هر سفارش (هر آیتم به یک سفارش و یک آیتم منو متصل است)"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(128), nullable=True)  # توضیحات برای آیتم (مثلاً بدون شکر)

    def __repr__(self):
        return f"<OrderItem {self.menu_item_id} x {self.quantity}>"

# --- مدل تنظیمات سیستم ---
class Settings(db.Model):
    """تنظیمات کلی سیستم (مثلاً درصد مالیات)"""
    id = db.Column(db.Integer, primary_key=True)
    tax_percent = db.Column(db.Float, nullable=False, default=9.0)
    cafe_name = db.Column(db.String(128), nullable=True)
    address = db.Column(db.String(256), nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    logo_url = db.Column(db.String(256), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Settings tax={self.tax_percent}>"

# --- مدل کاربر سیستم (ادمین/گارسون) ---
class User(db.Model, UserMixin):
    """کاربران سیستم (ادمین، گارسون و ...)"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(32), default='waiter')  # admin, waiter
    phone = db.Column(db.String(20), unique=True, nullable=True)
    created_at = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

# --- مدل لاگ عملیات (برای گزارش و امنیت) ---
class ActionLog(db.Model):
    """ثبت لاگ عملیات مهم (مثلاً حذف سفارش، پرداخت و ...)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(32), nullable=True)  # مثلاً Order, Customer
    target_id = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.String(256), nullable=True)

    user = db.relationship('User', backref='action_logs', lazy=True)

    def __repr__(self):
        return f"<ActionLog {self.action} on {self.target_type}:{self.target_id}>"

# --- توابع کمکی برای جستجو و ثبت مشتری ---
def find_or_create_customer(name: str, phone: str = None, email: str = None) -> Customer:
    """
    جستجو بر اساس نام یا شماره موبایل؛ اگر پیدا نشد، مشتری جدید ثبت می‌شود.
    """
    customer = None
    if phone:
        customer = Customer.query.filter_by(phone=phone).first()
    if not customer and name:
        customer = Customer.query.filter_by(name=name).first()
    if not customer:
        customer = Customer(name=name, phone=phone, email=email)
        db.session.add(customer)
        db.session.commit()
    return customer

# --- توابع کمکی برای تولید شماره فاکتور یکتا ---
def generate_invoice_number():
    """
    تولید شماره فاکتور یکتا (افزایش خودکار)
    """
    last_order = Order.query.order_by(Order.invoice_number.desc()).first()
    if last_order and last_order.invoice_number:
        return last_order.invoice_number + 1
    return 1001  # شروع از 1001

# --- توابع کمکی برای محاسبه مبلغ نهایی سفارش ---
def calculate_order_amount(order_items, discount=0, tax_percent=9.0):
    """
    محاسبه جمع کل، مالیات و مبلغ نهایی سفارش
    """
    total = sum(item['quantity'] * item['unit_price'] for item in order_items)
    tax = int(total * tax_percent / 100)
    final = total + tax - discount
    return total, tax, final
