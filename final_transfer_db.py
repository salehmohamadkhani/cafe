#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""انتقال نهایی دیتابیس با SQLite مستقیم"""
import os
import paramiko
import sqlite3
import time

SERVER_IP = os.environ.get("CAFE_SERVER_IP", "").strip()
SERVER_USER = os.environ.get("CAFE_SERVER_USER", "root").strip() or "root"
SERVER_PASSWORD = os.environ.get("CAFE_SERVER_PASSWORD", "")
REMOTE_PATH = os.environ.get("CAFE_REMOTE_PATH", "/var/www/کافه").strip() or "/var/www/کافه"
LOCAL_DB = "instance/cafe.db"

if not SERVER_IP or not SERVER_PASSWORD:
    raise RuntimeError("CAFE_SERVER_IP و CAFE_SERVER_PASSWORD باید در Environment Variables تنظیم شوند.")

python_code = f'''import sys
sys.path.insert(0, "/var/www/کافه")
import sqlite3
from app import create_app
from models.models import *
from datetime import datetime

app = create_app()
with app.app_context():
    print("="*60)
    print("📤 انتقال داده‌ها از دیتابیس محلی...")
    print("="*60)
    
    # اتصال به دیتابیس محلی
    local_conn = sqlite3.connect("/tmp/cafe_local.db")
    local_conn.row_factory = sqlite3.Row
    local_cursor = local_conn.cursor()
    
    transferred = {{}}
    
    # 1. Settings
    print("\\n📝 Settings...")
    settings_row = local_cursor.execute("SELECT * FROM settings LIMIT 1").fetchone()
    if settings_row:
        settings_dict = dict(settings_row)
        settings_id = settings_dict.pop("id")
        existing = Settings.query.first()
        if existing:
            for key, value in settings_dict.items():
                if hasattr(existing, key) and key != "id":
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            db.session.commit()
            print("✅ تنظیمات به‌روزرسانی شد")
        else:
            settings = Settings(**settings_dict)
            db.session.add(settings)
            db.session.commit()
            print("✅ تنظیمات ایجاد شد")
        transferred["settings"] = 1
    
    # 2. Categories
    print("\\n📁 Categories...")
    category_id_map = {{}}
    categories = local_cursor.execute("SELECT * FROM category").fetchall()
    for cat_row in categories:
        cat_dict = dict(cat_row)
        old_id = cat_dict.pop("id")
        # تبدیل datetime string به datetime object
        if "created_at" in cat_dict:
            created_at = cat_dict["created_at"]
            if isinstance(created_at, str):
                try:
                    from datetime import datetime as dt
                    cat_dict["created_at"] = dt.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f")
                except:
                    try:
                        cat_dict["created_at"] = dt.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    except:
                        cat_dict["created_at"] = datetime.utcnow()
            elif created_at is None:
                cat_dict["created_at"] = datetime.utcnow()
        existing = Category.query.filter_by(name=cat_dict["name"]).first()
        if not existing:
            cat = Category(**cat_dict)
            db.session.add(cat)
            db.session.flush()
            category_id_map[old_id] = cat.id
        else:
            category_id_map[old_id] = existing.id
    db.session.commit()
    transferred["categories"] = len(category_id_map)
    print(f"✅ {{len(category_id_map)}} دسته‌بندی منتقل شد")
    
    # 3. Menu Items
    print("\\n🍽️  Menu Items...")
    menu_count = 0
    menu_items = local_cursor.execute("SELECT * FROM menu_item").fetchall()
    for item_row in menu_items:
        item_dict = dict(item_row)
        old_cat_id = item_dict.pop("category_id")
        item_dict.pop("id", None)
        new_cat_id = category_id_map.get(old_cat_id)
        if new_cat_id:
            item_dict["category_id"] = new_cat_id
            # تبدیل datetime
            for date_field in ["created_at", "updated_at"]:
                if date_field in item_dict:
                    dt_val = item_dict[date_field]
                    if isinstance(dt_val, str):
                        try:
                            from datetime import datetime as dt
                            item_dict[date_field] = dt.strptime(dt_val, "%Y-%m-%d %H:%M:%S.%f")
                        except:
                            try:
                                item_dict[date_field] = dt.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
                            except:
                                item_dict[date_field] = datetime.utcnow()
                    elif dt_val is None:
                        item_dict[date_field] = datetime.utcnow()
            existing = MenuItem.query.filter_by(name=item_dict["name"]).first()
            if not existing:
                item = MenuItem(**item_dict)
                db.session.add(item)
                menu_count += 1
    db.session.commit()
    transferred["menu_items"] = menu_count
    print(f"✅ {{menu_count}} آیتم منو منتقل شد")
    
    # 4. Customers (100 مورد اول)
    print("\\n👥 Customers...")
    customer_count = 0
    customers = local_cursor.execute("SELECT * FROM customer LIMIT 100").fetchall()
    for cust_row in customers:
        cust_dict = dict(cust_row)
        cust_dict.pop("id", None)
        # تبدیل datetime
        for date_field in ["created_at", "last_visit"]:
            if date_field in cust_dict:
                dt_val = cust_dict[date_field]
                if isinstance(dt_val, str):
                    try:
                        from datetime import datetime as dt
                        cust_dict[date_field] = dt.strptime(dt_val, "%Y-%m-%d %H:%M:%S.%f")
                    except:
                        try:
                            cust_dict[date_field] = dt.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
                        except:
                            cust_dict[date_field] = datetime.utcnow() if date_field == "created_at" else None
                elif dt_val is None and date_field == "created_at":
                    cust_dict[date_field] = datetime.utcnow()
        phone = cust_dict.get("phone")
        if phone:
            existing = Customer.query.filter_by(phone=phone).first()
            if not existing:
                customer = Customer(**cust_dict)
                db.session.add(customer)
                customer_count += 1
    db.session.commit()
    transferred["customers"] = customer_count
    print(f"✅ {{customer_count}} مشتری منتقل شد")
    
    local_conn.close()
    
    # خلاصه
    print("\\n" + "="*60)
    print("📊 خلاصه انتقال:")
    print("="*60)
    for key, value in transferred.items():
        print(f"  {{key}}: {{value}}")
    print("="*60)
    print("\\n✅ انتقال کامل شد!")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD)

print("📤 کپی دیتابیس محلی به سرور...")
sftp = ssh.open_sftp()
sftp.put(LOCAL_DB, '/tmp/cafe_local.db')
sftp.close()
print("✅ دیتابیس کپی شد\n")

print("🔧 در حال انتقال داده‌ها...\n")
sftp = ssh.open_sftp()
with sftp.open(f'{REMOTE_PATH}/temp_final_transfer.py', 'w') as f:
    f.write(python_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command(f'cd {REMOTE_PATH} && source venv/bin/activate && python3 temp_final_transfer.py')
time.sleep(10)

output = stdout.read().decode('utf-8', errors='ignore')
errors = stderr.read().decode('utf-8', errors='ignore')

print(output)
if errors and 'Traceback' in errors:
    print("\n❌ خطا:", errors)

ssh.close()

