#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""انتقال داده‌های دیتابیس محلی به سرور"""
import os
import paramiko
import sqlite3
import json
import time
from datetime import datetime
from dateutil.parser import parse

SERVER_IP = os.environ.get("CAFE_SERVER_IP", "").strip()
SERVER_USER = os.environ.get("CAFE_SERVER_USER", "root").strip() or "root"
SERVER_PASSWORD = os.environ.get("CAFE_SERVER_PASSWORD", "")
REMOTE_PATH = os.environ.get("CAFE_REMOTE_PATH", "/var/www/کافه").strip() or "/var/www/کافه"
LOCAL_DB = "instance/cafe.db"

if not SERVER_IP or not SERVER_PASSWORD:
    raise RuntimeError("CAFE_SERVER_IP و CAFE_SERVER_PASSWORD باید در Environment Variables تنظیم شوند.")

print("="*60)
print("🚀 انتقال داده‌های دیتابیس به سرور")
print("="*60)

# اتصال به دیتابیس محلی
print("\n📂 اتصال به دیتابیس محلی...")
local_conn = sqlite3.connect(LOCAL_DB)
local_conn.row_factory = sqlite3.Row
local_cursor = local_conn.cursor()

# کد Python برای اجرا در سرور
python_code = f'''import sys
sys.path.insert(0, "/var/www/کافه")
from app import create_app
from models.models import *
from datetime import datetime
import json

def parse_datetime(dt_str):
    """تبدیل string به datetime"""
    if not dt_str:
        return None
    if isinstance(dt_str, datetime):
        return dt_str
    try:
        # فرمت‌های مختلف
        for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(dt_str, fmt)
            except:
                continue
        return datetime.utcnow()
    except:
        return datetime.utcnow()

app = create_app()
with app.app_context():
    print("="*60)
    print("📤 دریافت و ذخیره داده‌ها در سرور...")
    print("="*60)
    
    # دریافت داده‌ها از stdin
    import sys
    data_json = sys.stdin.read()
    data = json.loads(data_json)
    
    transferred = {{}}
    
    # 1. Settings
    if data.get("settings"):
        settings_data = data["settings"]
        existing = Settings.query.first()
        if existing:
            for key, value in settings_data.items():
                if hasattr(existing, key) and key != "id":
            # تبدیل datetime string
            if isinstance(value, str) and ("updated_at" in key or "created_at" in key):
                value = parse_datetime(value)
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            db.session.commit()
            print("✅ تنظیمات به‌روزرسانی شد")
        else:
            settings = Settings(**settings_data)
            db.session.add(settings)
            db.session.commit()
            print("✅ تنظیمات ایجاد شد")
        transferred["settings"] = 1
    
    # 2. Categories
    category_id_map = {{}}
    if data.get("categories"):
        for cat_data in data["categories"]:
            old_id = cat_data.pop("id")
            # تبدیل datetime string به datetime object
            if "created_at" in cat_data and isinstance(cat_data["created_at"], str):
                cat_data["created_at"] = parse_datetime(cat_data["created_at"])
            existing = Category.query.filter_by(name=cat_data["name"]).first()
            if not existing:
                cat = Category(**cat_data)
                db.session.add(cat)
                db.session.flush()
                category_id_map[old_id] = cat.id
                print(f"  ✅ دسته‌بندی: {{cat.name}}")
            else:
                category_id_map[old_id] = existing.id
        db.session.commit()
        transferred["categories"] = len(category_id_map)
        print(f"✅ {{len(category_id_map)}} دسته‌بندی منتقل شد")
    
    # 3. Menu Items (باید بعد از categories باشد)
    if data.get("menu_items") and category_id_map:
        menu_count = 0
        for item_data in data["menu_items"]:
            old_cat_id = item_data.get("category_id")
            new_cat_id = category_id_map.get(old_cat_id) if old_cat_id else None
            if new_cat_id:
                item_data["category_id"] = new_cat_id
                # تبدیل datetime
                for date_field in ["created_at", "updated_at"]:
                    if date_field in item_data and isinstance(item_data[date_field], str):
                        item_data[date_field] = parse_datetime(item_data[date_field])
                existing = MenuItem.query.filter_by(name=item_data["name"]).first()
                if not existing:
                    item = MenuItem(**item_data)
                    db.session.add(item)
                    menu_count += 1
        db.session.commit()
        transferred["menu_items"] = menu_count
        print(f"✅ {{menu_count}} آیتم منو منتقل شد")
    
    # 4. Customers
    if data.get("customers"):
        customer_count = 0
        for cust_data in data["customers"]:
            cust_data.pop("id", None)
            existing = Customer.query.filter_by(phone=cust_data.get("phone")).first()
            if not existing and cust_data.get("phone"):
                customer = Customer(**cust_data)
                db.session.add(customer)
                customer_count += 1
        db.session.commit()
        transferred["customers"] = customer_count
        print(f"✅ {{customer_count}} مشتری منتقل شد")
    
    # خلاصه
    print("\\n" + "="*60)
    print("📊 خلاصه انتقال:")
    print("="*60)
    for key, value in transferred.items():
        print(f"  {{key}}: {{value}}")
    print("="*60)
    print("\\n✅ انتقال کامل شد!")
'''

# جمع‌آوری داده‌ها از دیتابیس محلی
print("\n📦 جمع‌آوری داده‌ها...")

data = {}

# Settings
print("  📝 Settings...")
settings_row = local_cursor.execute("SELECT * FROM settings LIMIT 1").fetchone()
if settings_row:
    settings_dict = dict(settings_row)
    settings_dict.pop("id", None)
    # تبدیل datetime به string
    for key, value in settings_dict.items():
        if isinstance(value, datetime):
            settings_dict[key] = value.isoformat()
    data["settings"] = settings_dict

# Categories
print("  📁 Categories...")
categories = []
category_rows = local_cursor.execute("SELECT * FROM category").fetchall()
for row in category_rows:
    cat_dict = dict(row)
    categories.append(cat_dict)
data["categories"] = categories

# Menu Items
print("  🍽️  Menu Items...")
menu_items = []
menu_rows = local_cursor.execute("SELECT * FROM menu_item").fetchall()
for row in menu_rows:
    item_dict = dict(row)
    item_dict.pop("id", None)  # ID جدید ایجاد می‌شود
    menu_items.append(item_dict)
data["menu_items"] = menu_items

# Customers (فقط 100 تا اول برای تست)
print("  👥 Customers (100 مورد اول)...")
customers = []
customer_rows = local_cursor.execute("SELECT * FROM customer LIMIT 100").fetchall()
for row in customer_rows:
    cust_dict = dict(row)
    cust_dict.pop("id", None)
    customers.append(cust_dict)
data["customers"] = customers

local_conn.close()

# اتصال به سرور و ارسال داده‌ها
print("\n📤 ارسال داده‌ها به سرور...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD)

# نوشتن کد در سرور
sftp = ssh.open_sftp()
with sftp.open(f'{REMOTE_PATH}/temp_transfer_data.py', 'w') as f:
    f.write(python_code)
sftp.close()

# ارسال داده‌ها و اجرا
data_json = json.dumps(data, default=str)
command = f'cd {REMOTE_PATH} && source venv/bin/activate && python3 temp_transfer_data.py'
stdin, stdout, stderr = ssh.exec_command(command)
stdin.write(data_json)
stdin.close()

time.sleep(8)

output = stdout.read().decode('utf-8', errors='ignore')
errors = stderr.read().decode('utf-8', errors='ignore')

print("\n" + output)
if errors and 'Traceback' in errors:
    print("\n❌ خطا:", errors)

ssh.close()

print("\n✅ انتقال داده‌ها کامل شد!")

