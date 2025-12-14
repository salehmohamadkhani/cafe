#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسی ساختار دیتابیس در سرور"""
import os
import paramiko
import time

SERVER_IP = os.environ.get("CAFE_SERVER_IP", "").strip()
SERVER_USER = os.environ.get("CAFE_SERVER_USER", "root").strip() or "root"
SERVER_PASSWORD = os.environ.get("CAFE_SERVER_PASSWORD", "")
REMOTE_PATH = os.environ.get("CAFE_REMOTE_PATH", "/var/www/کافه").strip() or "/var/www/کافه"

if not SERVER_IP or not SERVER_PASSWORD:
    raise RuntimeError("CAFE_SERVER_IP و CAFE_SERVER_PASSWORD باید در Environment Variables تنظیم شوند.")

python_code = '''import sys
sys.path.insert(0, "/var/www/کافه")
from app import create_app
from models.models import *
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    engine = db.get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print("="*60)
    print("📊 ساختار دیتابیس:")
    print("="*60)
    print(f"تعداد جداول: {len(tables)}")
    print("\\nجداول موجود:")
    for table in sorted(tables):
        columns = inspector.get_columns(table)
        print(f"  ✓ {table} ({len(columns)} ستون)")
    
    # بررسی داده‌ها
    print("\\n" + "="*60)
    print("📦 داده‌های موجود:")
    print("="*60)
    
    from models.models import User, Category, MenuItem, Customer, Table, Settings, RawMaterial
    
    user_count = User.query.count()
    category_count = Category.query.count()
    menu_count = MenuItem.query.count()
    customer_count = Customer.query.count()
    table_count = Table.query.count()
    settings_count = Settings.query.count()
    material_count = RawMaterial.query.count()
    
    print(f"👤 کاربران: {user_count}")
    print(f"📁 دسته‌بندی‌ها: {category_count}")
    print(f"🍽️  آیتم‌های منو: {menu_count}")
    print(f"👥 مشتریان: {customer_count}")
    print(f"🪑 میزها: {table_count}")
    print(f"⚙️  تنظیمات: {settings_count}")
    print(f"📦 مواد اولیه: {material_count}")
    
    # بررسی Settings
    settings = Settings.query.first()
    if settings:
        print(f"\\n✅ تنظیمات کافه:")
        print(f"   نام: {settings.cafe_name}")
    else:
        print("\\n⚠️  تنظیمات کافه وجود ندارد!")
    
    print("="*60)
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD)

print("🔍 بررسی ساختار دیتابیس...\n")

sftp = ssh.open_sftp()
with sftp.open(f'{REMOTE_PATH}/temp_check_db.py', 'w') as f:
    f.write(python_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command(f'cd {REMOTE_PATH} && source venv/bin/activate && python3 temp_check_db.py')
time.sleep(4)

output = stdout.read().decode('utf-8', errors='ignore')
errors = stderr.read().decode('utf-8', errors='ignore')

print(output)
if errors and 'Traceback' in errors:
    print("\n❌ خطا:", errors)

ssh.close()

