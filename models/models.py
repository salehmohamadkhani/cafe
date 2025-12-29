from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from typing import Optional
import pytz
from flask_login import UserMixin
from dataclasses import dataclass

iran_tz = pytz.timezone("Asia/Tehran")

UNIT_SYNONYMS = {
    'gr': 'g',
    'g': 'g',
    'گرم': 'g',
    'گریم': 'g',
    'کیلو': 'kg',
    'کیلوگرم': 'kg',
    'kg': 'kg',
    'میلی لیتر': 'ml',
    'میلی‌لیتر': 'ml',
    'میلی لیتر': 'ml',
    'ml': 'ml',
    'cc': 'ml',
    'سی سی': 'ml',
    'l': 'l',
    'لیتر': 'l',
    'عدد': 'count',
    'تعداد': 'count',
    'pcs': 'count',
    'piece': 'count',
    'تیکه': 'count',
    'بسته': 'pack',
    'pack': 'pack',
    'متر': 'm',
    'meter': 'm',
    'm': 'm'
}


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    key = str(unit).strip().lower()
    return UNIT_SYNONYMS.get(key, key)


def convert_unit(quantity: Optional[float], from_unit: Optional[str], to_unit: Optional[str]) -> float:
    if quantity is None:
        return 0.0
    from_norm = normalize_unit(from_unit) or normalize_unit(to_unit)
    to_norm = normalize_unit(to_unit) or normalize_unit(from_unit)
    if not from_norm or not to_norm or from_norm == to_norm:
        return float(quantity)

    if from_norm == 'kg' and to_norm == 'g':
        return float(quantity) * 1000
    if from_norm == 'g' and to_norm == 'kg':
        return float(quantity) / 1000
    if from_norm == 'l' and to_norm == 'ml':
        return float(quantity) * 1000
    if from_norm == 'ml' and to_norm == 'l':
        return float(quantity) / 1000
    if from_norm == 'count' and to_norm == 'count':
        return float(quantity)
    if from_norm == 'pack' and to_norm == 'pack':
        return float(quantity)
    if from_norm == 'm' and to_norm == 'm':
        return float(quantity)

    return float(quantity)

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
    materials = db.relationship(
        'MenuItemMaterial',
        backref='menu_item',
        lazy=True,
        cascade='all, delete-orphan'
    )

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
    birth_date = db.Column(db.Date, nullable=True)  # تاریخ تولد مشتری
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
    daily_sequence = db.Column(db.Integer, nullable=True)
    invoice_uid = db.Column(db.String(64), unique=True, nullable=True)
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
    payment_method = db.Column(db.String(32), nullable=True)  # کارتخوان، کارت به کارت و ...
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # اضافه کردن فیلد user_id
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=True)  # میز مرتبط با این سفارش

    order_items = db.relationship(
    'OrderItem',
    backref='order',
    lazy=True,
    cascade='all, delete-orphan'
    )
    
    # Relationship به Table از طریق table_id
    # از foreign_keys استفاده می‌کنیم تا مشخص کنیم از table_id استفاده شود نه order_id
    table = db.relationship('Table', foreign_keys=[table_id], lazy=True)


    def __repr__(self):
        human_code = self.invoice_uid or self.invoice_number
        return f"<Order #{human_code} - {self.status}>"

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
    removal_reason = db.Column(db.String(256), nullable=True)  # دلیل حذف آیتم
    is_deleted = db.Column(db.Boolean, default=False)  # نشان می‌دهد که آیا آیتم حذف شده است یا نه

    material_usages = db.relationship(
        'RawMaterialUsage',
        backref='order_item',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<OrderItem {self.menu_item_id} x {self.quantity}>"

# --- مدل تنظیمات سیستم ---
class Settings(db.Model):
    """تنظیمات کلی سیستم (مثلاً درصد مالیات)"""
    id = db.Column(db.Integer, primary_key=True)
    tax_percent = db.Column(db.Float, nullable=False, default=9.0)
    service_charge = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(16), nullable=False, default='')
    card_number = db.Column(db.String(64), nullable=True)
    cafe_name = db.Column(db.String(128), nullable=True)
    address = db.Column(db.String(256), nullable=True)
    phone = db.Column(db.String(32), nullable=True)
    logo_url = db.Column(db.String(256), nullable=True)
    instagram = db.Column(db.String(256), nullable=True)
    telegram = db.Column(db.String(256), nullable=True)
    website = db.Column(db.String(256), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Settings tax={self.tax_percent}>"


class CostFormulaSettings(db.Model):
    """تنظیمات فرمول محاسبه بهای تمام‌شده (پرسنل، اجاره، استهلاک و آمار سفارش‌ها)"""
    id = db.Column(db.Integer, primary_key=True)

    # نیروی انسانی
    staff_count = db.Column(db.Integer, default=0)
    total_staff_salary = db.Column(db.Integer, default=0)  # مجموع حقوق ماهانه همه پرسنل (به تومان)
    personnel = db.Column(db.JSON, default=list)  # [{name, salary}]

    # اجاره
    has_rent = db.Column(db.Boolean, default=False)
    rent_amount = db.Column(db.Integer, default=0)  # تومان

    # استهلاک تجهیزات
    depreciation = db.Column(db.Integer, default=0)  # تومان

    # آمار سفارش‌ها
    monthly_orders_avg = db.Column(db.Integer, default=0)
    avg_order_price = db.Column(db.Integer, default=0)

    # درصد کاست کنترل (برای حاشیه اطمینان روی هزینه‌ها)
    cost_control_percent = db.Column(db.Integer, default=0)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CostFormulaSettings staff={self.staff_count} rent={self.rent_amount}>"

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

# --- مدل میز کافه ---
class TableArea(db.Model):
    """دسته‌بندی میزها (مثلاً سالن اصلی، تراس و ...)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))

    tables = db.relationship('Table', backref='area', lazy=True)

    def __repr__(self):
        return f"<TableArea {self.name}>"


class Table(db.Model):
    """میزهای کافه"""
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)  # شماره میز
    status = db.Column(db.String(32), default='خالی')  # خالی، اشغال شده
    is_reserved = db.Column(db.Boolean, default=False)  # آیا میز رزرو شده است
    customer_name = db.Column(db.String(128), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    total_amount = db.Column(db.Integer, default=0)
    discount = db.Column(db.Integer, default=0)
    tax_amount = db.Column(db.Integer, default=0)
    final_amount = db.Column(db.Integer, default=0)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)  # سفارش مرتبط
    area_id = db.Column(db.Integer, db.ForeignKey('table_area.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz), onupdate=lambda: datetime.now(iran_tz))
    
    # Relationship به Order از طریق order_id (سفارش فعلی میز)
    # از foreign_keys استفاده می‌کنیم تا مشخص کنیم از order_id استفاده شود نه table_id
    order = db.relationship('Order', foreign_keys=[order_id], lazy=True)
    
    def __repr__(self):
        area_label = self.area.name if self.area else 'بدون دسته'
        return f"<Table {self.number} ({area_label}) - {self.status}>"

# --- مدل آیتم‌های میز (موقت قبل از ثبت سفارش) ---
class TableItem(db.Model):
    """آیتم‌های انتخاب شده برای میز (قبل از ثبت سفارش)"""
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    
    table = db.relationship('Table', backref=db.backref('table_items', lazy=True, cascade='all, delete-orphan'))
    menu_item = db.relationship('MenuItem', backref='table_items', lazy=True)
    
    def __repr__(self):
        return f"<TableItem {self.menu_item_id} x {self.quantity}>"

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


class SnapSettlement(db.Model):
    """
    ثبت تسویه‌های اسنپ به صورت دستی.

    منطق استفاده:
    - سفارش‌هایی که payment_method آنها در باکت 'snap' قرار می‌گیرد، تا زمانی که در یک بازه تسویه ثبت نشوند،
      به عنوان "مطالبات اسنپ" (دریافت نشده) در گزارش مالی نمایش داده می‌شوند.
    - کاربر می‌تواند برای یک بازه (start_date تا end_date) تسویه را ثبت کند تا مبالغ آن بازه در گزارش‌ها "تسویه‌شده" محسوب شود.
    """
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    settled_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    note = db.Column(db.String(256), nullable=True)

    user = db.relationship('User', backref='snap_settlements', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('start_date', 'end_date', name='uq_snap_settlement_period'),
    )

    def __repr__(self):
        status = 'settled' if self.settled_at else 'pending'
        return f"<SnapSettlement {self.start_date}..{self.end_date} {status}>"


class MenuItemMaterial(db.Model):
    """مواد اولیه یا محصولات پیش تولید مورد نیاز هر آیتم منو"""
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=True)
    pre_production_item_id = db.Column(db.Integer, db.ForeignKey('pre_production_item.id'), nullable=True)
    name = db.Column(db.String(128), nullable=False)
    quantity = db.Column(db.String(64), nullable=False)
    unit = db.Column(db.String(32), nullable=False, default='عدد')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))

    raw_material = db.relationship('RawMaterial', backref='menu_materials', lazy=True)
    pre_production_item = db.relationship('PreProductionItem', backref='menu_materials', lazy=True)

    @property
    def quantity_value(self):
        try:
            return float(self.quantity)
        except (TypeError, ValueError):
            return None

    @property
    def latest_unit_price(self):
        if self.raw_material:
            return self.raw_material.latest_unit_price
        elif self.pre_production_item:
            # محاسبه قیمت محصول پیش تولید بر اساس مواد اولیه تشکیل‌دهنده آن
            total_cost = 0.0
            for item_material in self.pre_production_item.materials:
                raw_material = item_material.raw_material
                if not raw_material:
                    continue
                
                # قیمت واحد ماده اولیه (در واحد default ماده اولیه)
                unit_price = raw_material.latest_unit_price
                if unit_price is None:
                    continue
                
                # مقدار ماده اولیه در واحد خودش
                material_qty = item_material.quantity
                try:
                    material_qty_float = float(material_qty)
                except (TypeError, ValueError):
                    continue
                
                # تبدیل مقدار ماده اولیه به واحد default ماده اولیه
                material_qty_in_base_unit = convert_unit(material_qty_float, item_material.unit, raw_material.default_unit)
                
                # هزینه این ماده اولیه برای یک واحد محصول پیش تولید
                # unit_price در واحد default ماده اولیه است
                material_cost = material_qty_in_base_unit * unit_price
                total_cost += material_cost
            
            return int(total_cost) if total_cost > 0 else None
        return None

    @property
    def estimated_cost(self):
        qty = self.quantity_value
        unit_price = self.latest_unit_price
        if qty is None or unit_price is None:
            return None
        return qty * unit_price

    def __repr__(self):
        return f"<MenuItemMaterial {self.name} ({self.quantity} {self.unit}) for {self.menu_item_id}>"


class RawMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    default_unit = db.Column(db.String(32), nullable=False, default='gr')
    description = db.Column(db.String(256), nullable=True)
    min_stock = db.Column(db.Float, nullable=True)  # حداقل موجودی
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz), onupdate=lambda: datetime.now(iran_tz))

    purchases = db.relationship('MaterialPurchase', backref='raw_material', lazy='dynamic', cascade='all, delete-orphan')
    usages = db.relationship('RawMaterialUsage', backref='raw_material', lazy=True, cascade='all, delete-orphan')

    @property
    def latest_purchase(self):
        if self.purchases is None:
            return None
        return self.purchases.order_by(MaterialPurchase.purchase_date.desc(), MaterialPurchase.created_at.desc()).first()

    @property
    def latest_unit_price(self):
        purchase = self.latest_purchase
        if purchase:
            return purchase.unit_price
        return None

    @property
    def total_purchase_value(self):
        return sum(p.total_price for p in self.purchases)
    
    @property
    def current_stock(self):
        """محاسبه موجودی فعلی از خریدها"""
        base_unit = self.default_unit
        total = 0.0
        for purchase in self.purchases:
            total += convert_unit(purchase.quantity, purchase.unit, base_unit)

        usage_total = 0.0
        for usage in self.usages:
            usage_total += convert_unit(usage.quantity, usage.unit, base_unit)

        remaining = total - usage_total
        return remaining if remaining > 0 else 0.0

    def __repr__(self):
        return f"<RawMaterial {self.name}>"


class MaterialPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=False)
    purchase_date = db.Column(db.Date, default=lambda: datetime.now(iran_tz).date())
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(32), nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    vendor_name = db.Column(db.String(128), nullable=True)
    vendor_phone = db.Column(db.String(32), nullable=True)
    note = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))

    @property
    def unit_price(self):
        if not self.quantity:
            return 0
        return int(self.total_price / self.quantity)

    def __repr__(self):
        return f"<MaterialPurchase {self.raw_material_id} {self.purchase_date}>"


class RawMaterialUsage(db.Model):
    """ثبت مصرف مواد اولیه برای هر سفارش/آیتم"""
    id = db.Column(db.Integer, primary_key=True)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id', ondelete='CASCADE'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_item.id', ondelete='CASCADE'), nullable=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=True)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(32), nullable=False)
    note = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))

    menu_item = db.relationship('MenuItem', backref='material_usages', lazy=True)
    order = db.relationship('Order', backref='material_usages', lazy=True)

    def __repr__(self):
        return f"<RawMaterialUsage material={self.raw_material_id} qty={self.quantity} {self.unit}>"


class Warehouse(db.Model):
    """انبارهای فیزیکی (مثلاً انبار مرکزی، آشپزخانه‌ها، قلیان و ...)"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)  # central, kitchen_western, ...
    name = db.Column(db.String(128), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))

    def __repr__(self):
        return f"<Warehouse {self.code} {self.name}>"


class WarehouseTransfer(db.Model):
    """
    انتقال موجودی بین انبارها.

    نکته مهم:
    - base_quantity همیشه در واحد پایه ماده اولیه (RawMaterial.default_unit) ذخیره می‌شود تا محاسبه موجودی سریع باشد.
    """
    id = db.Column(db.Integer, primary_key=True)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=False, index=True)
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True, index=True)
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True, index=True)

    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(32), nullable=False)
    base_quantity = db.Column(db.Float, nullable=False)  # converted to raw_material.default_unit

    transfer_date = db.Column(db.Date, default=lambda: datetime.now(iran_tz).date(), index=True)
    note = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    raw_material = db.relationship('RawMaterial', backref=db.backref('warehouse_transfers', lazy=True))
    from_warehouse = db.relationship('Warehouse', foreign_keys=[from_warehouse_id], lazy=True)
    to_warehouse = db.relationship('Warehouse', foreign_keys=[to_warehouse_id], lazy=True)
    user = db.relationship('User', backref='warehouse_transfers', lazy=True)

    def __repr__(self):
        return f"<WarehouseTransfer rm={self.raw_material_id} {self.from_warehouse_id}->{self.to_warehouse_id} qty={self.quantity} {self.unit}>"


class WarehouseMaterialMinStock(db.Model):
    """حداقل موجودی هر ماده اولیه در هر انبار"""
    id = db.Column(db.Integer, primary_key=True)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False, index=True)
    min_stock = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz), onupdate=lambda: datetime.now(iran_tz))

    raw_material = db.relationship('RawMaterial', backref=db.backref('warehouse_min_stocks', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('material_min_stocks', lazy=True))

    __table_args__ = (db.UniqueConstraint('raw_material_id', 'warehouse_id', name='uq_warehouse_material_min_stock'),)

    def __repr__(self):
        return f"<WarehouseMaterialMinStock rm={self.raw_material_id} wh={self.warehouse_id} min={self.min_stock}>"


class PreProductionItem(db.Model):
    """محصولات پیش تولید (مثل burger, pizza و...)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    code = db.Column(db.String(64), unique=True, nullable=True)
    description = db.Column(db.String(512), nullable=True)
    unit = db.Column(db.String(32), nullable=False, default='عدد')  # واحد محصول (عدد، کیلو، ...)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz), onupdate=lambda: datetime.now(iran_tz))

    # Relationship to materials
    materials = db.relationship('PreProductionItemMaterial', backref='pre_production_item', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<PreProductionItem {self.name}>"


class PreProductionItemMaterial(db.Model):
    """مواد اولیه مورد نیاز برای تولید هر محصول پیش تولید (رسپی)"""
    id = db.Column(db.Integer, primary_key=True)
    pre_production_item_id = db.Column(db.Integer, db.ForeignKey('pre_production_item.id'), nullable=False, index=True)
    raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_material.id'), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)  # مقدار ماده اولیه
    unit = db.Column(db.String(32), nullable=False)  # واحد ماده اولیه
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))

    raw_material = db.relationship('RawMaterial', backref=db.backref('pre_production_usage', lazy=True))

    def __repr__(self):
        return f"<PreProductionItemMaterial item={self.pre_production_item_id} material={self.raw_material_id} qty={self.quantity} {self.unit}>"


class PreProductionStock(db.Model):
    """موجودی محصولات پیش تولید در انبارها"""
    id = db.Column(db.Integer, primary_key=True)
    pre_production_item_id = db.Column(db.Integer, db.ForeignKey('pre_production_item.id'), nullable=False, index=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(32), nullable=False, default='عدد')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz), onupdate=lambda: datetime.now(iran_tz))

    pre_production_item = db.relationship('PreProductionItem', backref=db.backref('stock', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('pre_production_stocks', lazy=True))

    __table_args__ = (db.UniqueConstraint('pre_production_item_id', 'warehouse_id', name='uq_pre_production_stock'),)

    def __repr__(self):
        return f"<PreProductionStock item={self.pre_production_item_id} wh={self.warehouse_id} qty={self.quantity} {self.unit}>"


class PreProductionProduction(db.Model):
    """تاریخچه تولید محصولات پیش تولید"""
    id = db.Column(db.Integer, primary_key=True)
    pre_production_item_id = db.Column(db.Integer, db.ForeignKey('pre_production_item.id'), nullable=False, index=True)
    source_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)  # تعداد محصول تولید شده
    unit = db.Column(db.String(32), nullable=False, default='عدد')
    production_date = db.Column(db.Date, default=lambda: datetime.now(iran_tz).date(), index=True)
    note = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    pre_production_item = db.relationship('PreProductionItem', backref=db.backref('productions', lazy=True))
    source_warehouse = db.relationship('Warehouse', foreign_keys=[source_warehouse_id], backref=db.backref('pre_production_sources', lazy=True))
    user = db.relationship('User', backref='pre_production_productions', lazy=True)

    def __repr__(self):
        return f"<PreProductionProduction item={self.pre_production_item_id} qty={self.quantity} from_wh={self.source_warehouse_id}>"


class PreProductionTransfer(db.Model):
    """انتقال محصولات پیش تولید بین انبارها"""
    id = db.Column(db.Integer, primary_key=True)
    pre_production_item_id = db.Column(db.Integer, db.ForeignKey('pre_production_item.id'), nullable=False, index=True)
    from_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True, index=True)
    to_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True, index=True)
    
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(32), nullable=False)
    
    transfer_date = db.Column(db.Date, default=lambda: datetime.now(iran_tz).date(), index=True)
    note = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(iran_tz))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    pre_production_item = db.relationship('PreProductionItem', backref=db.backref('transfers', lazy=True))
    from_warehouse = db.relationship('Warehouse', foreign_keys=[from_warehouse_id], lazy=True)
    to_warehouse = db.relationship('Warehouse', foreign_keys=[to_warehouse_id], lazy=True)
    user = db.relationship('User', backref='pre_production_transfers', lazy=True)
    
    def __repr__(self):
        return f"<PreProductionTransfer item={self.pre_production_item_id} {self.from_warehouse_id}->{self.to_warehouse_id} qty={self.quantity} {self.unit}>"

# --- توابع کمکی برای جستجو و ثبت مشتری ---
def find_or_create_customer(name: str, phone: str = None, email: str = None, birth_date = None) -> Customer:
    """
    جستجو بر اساس نام یا شماره موبایل؛ اگر پیدا نشد، مشتری جدید ثبت می‌شود.
    """
    customer = None
    if phone:
        customer = Customer.query.filter_by(phone=phone).first()
    if not customer and name:
        customer = Customer.query.filter_by(name=name).first()
    if not customer:
        customer = Customer(name=name, phone=phone, email=email, birth_date=birth_date)
        db.session.add(customer)
        db.session.commit()
    elif birth_date and not customer.birth_date:
        # اگر مشتری قدیمی است و تاریخ تولد ندارد، آن را اضافه کن
        customer.birth_date = birth_date
        db.session.commit()
    return customer

@dataclass
class InvoiceIdentifiers:
    """شناسه‌های مورد نیاز برای ثبت فاکتور"""
    unique_number: int
    daily_sequence: int
    invoice_uid: str


def generate_invoice_number(now: Optional[datetime] = None) -> InvoiceIdentifiers:
    """
    محاسبه شماره فاکتور بعدی شامل:
    - unique_number: ادامه توالی قبلی (برای یکتا بودن در سیستم)
    - daily_sequence: ریست‌شونده روزانه که از 100 شروع می‌شود
    - invoice_uid: شناسه متنی ترکیبی از تاریخ + شماره روزانه (برای استفاده‌های آتی)
    """
    current_dt = now or datetime.now(iran_tz)

    last_order = Order.query.order_by(Order.invoice_number.desc()).first()
    if last_order and last_order.invoice_number:
        next_unique = last_order.invoice_number + 1
    else:
        next_unique = 1001

    start_of_day = current_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    last_today = (
        Order.query
        .filter(Order.created_at >= start_of_day, Order.created_at < end_of_day)
        .order_by(Order.daily_sequence.desc())
        .first()
    )

    next_daily = 100
    if last_today and last_today.daily_sequence:
        next_daily = last_today.daily_sequence + 1

    invoice_uid = f"{current_dt.strftime('%Y%m%d')}-{next_daily:04d}"

    return InvoiceIdentifiers(
        unique_number=next_unique,
        daily_sequence=next_daily,
        invoice_uid=invoice_uid
    )

# --- توابع کمکی برای محاسبه مبلغ نهایی سفارش ---
def calculate_order_amount(order_items, discount=0, tax_percent=9.0):
    """
    محاسبه جمع کل، مالیات و مبلغ نهایی سفارش
    """
    total = sum(item['quantity'] * item['unit_price'] for item in order_items)
    tax = int(total * tax_percent / 100)
    final = total + tax - discount
    return total, tax, final


def sync_order_item_material_usage(order_item):
    """همگام‌سازی مصرف مواد اولیه برای یک آیتم سفارش"""
    if not order_item:
        return

    if order_item.id is None:
        db.session.flush()

    RawMaterialUsage.query.filter_by(order_item_id=order_item.id).delete()

    menu_item = order_item.menu_item or MenuItem.query.get(order_item.menu_item_id)
    if not menu_item:
        return

    for material in menu_item.materials:
        raw_material = material.raw_material
        qty_per_unit = material.quantity_value
        if not raw_material or qty_per_unit is None:
            continue

        total_qty = qty_per_unit * order_item.quantity
        usage_unit = material.unit or raw_material.default_unit
        usage = RawMaterialUsage(
            raw_material_id=raw_material.id,
            order_id=order_item.order_id,
            order_item_id=order_item.id,
            menu_item_id=menu_item.id,
            quantity=total_qty,
            unit=usage_unit
        )
        db.session.add(usage)


def record_order_material_usage(order, replace_existing=False):
    """ثبت/به‌روزرسانی مصرف مواد اولیه برای کل سفارش"""
    if not order:
        return

    if replace_existing and order.id is not None:
        RawMaterialUsage.query.filter_by(order_id=order.id).delete()

    for order_item in order.order_items:
        sync_order_item_material_usage(order_item)


def _normalize_created_at(created_at: Optional[datetime]) -> Optional[datetime]:
    if not created_at:
        return None
    if created_at.tzinfo is None:
        try:
            return iran_tz.localize(created_at)
        except ValueError:
            return created_at.replace(tzinfo=iran_tz)
    return created_at.astimezone(iran_tz)


def backfill_invoice_identifiers():
    """
    برای سفارش‌های قدیمی که daily_sequence یا invoice_uid ندارند،
    مقادیر مناسب را محاسبه و ذخیره می‌کند.
    """
    from collections import defaultdict

    orders = Order.query.order_by(Order.created_at.asc(), Order.id.asc()).all()
    if not orders:
        return

    daily_track = defaultdict(lambda: 99)
    changes = False

    for order in orders:
        localized_dt = _normalize_created_at(order.created_at)
        order_date = localized_dt.date() if localized_dt else None

        if order_date:
            if not order.daily_sequence or order.daily_sequence < 100:
                daily_track[order_date] += 1
                order.daily_sequence = daily_track[order_date]
                changes = True
            else:
                daily_track[order_date] = max(daily_track[order_date], order.daily_sequence)

            if not order.invoice_uid:
                order.invoice_uid = f"{order_date.strftime('%Y%m%d')}-{order.daily_sequence:04d}"
                changes = True
        else:
            if not order.invoice_uid:
                order.invoice_uid = f"LEGACY-{order.invoice_number}"
                changes = True

    if changes:
        db.session.commit()


def assign_random_birth_dates_to_old_customers():
    """
    اختصاص تاریخ تولد تصادفی به مشتریان قدیمی که تاریخ تولد ندارند
    """
    from random import randint
    from datetime import date, timedelta
    
    # پیدا کردن مشتریانی که سفارش دارند اما تاریخ تولد ندارند
    customers_with_orders = (
        db.session.query(Customer)
        .join(Order, Order.customer_id == Customer.id)
        .filter(Customer.birth_date.is_(None))
        .distinct()
        .all()
    )
    
    changes = False
    for customer in customers_with_orders:
        # تولید تاریخ تولد تصادفی بین 18 تا 80 سال پیش
        years_ago = randint(18, 80)
        days_ago = randint(0, 365)
        birth_date = date.today() - timedelta(days=years_ago * 365 + days_ago)
        customer.birth_date = birth_date
        changes = True
    
    if changes:
        db.session.commit()
        print(f"تاریخ تولد تصادفی به {len(customers_with_orders)} مشتری قدیمی اختصاص داده شد")
    
    return len(customers_with_orders)
