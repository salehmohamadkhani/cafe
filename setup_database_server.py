#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ایجاد و تنظیم دیتابیس کامل در سرور"""
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
from datetime import datetime
from utils.seed_inventory import seed_inventory_if_needed

app = create_app()
with app.app_context():
    print("="*60)
    print("🔧 تنظیم دیتابیس...")
    print("="*60)
    
    # 1. ایجاد Settings اولیه
    settings = Settings.query.first()
    if not settings:
        print("\\n📝 ایجاد تنظیمات اولیه...")
        settings = Settings(
            cafe_name="کافه مادلین",
            phone="",
            address="",
            tax_percent=9.0,
            service_charge=0.0,
            currency="",
            updated_at=datetime.utcnow()
        )
        db.session.add(settings)
        db.session.commit()
        print("✅ تنظیمات اولیه ایجاد شد")
    else:
        print(f"\\n✅ تنظیمات موجود: {settings.cafe_name}")
    
    # 2. Seed مواد اولیه
    print("\\n📦 بررسی مواد اولیه...")
    material_count_before = RawMaterial.query.count()
    seed_inventory_if_needed()
    material_count_after = RawMaterial.query.count()
    if material_count_after > material_count_before:
        print(f"✅ {material_count_after - material_count_before} ماده اولیه اضافه شد")
    else:
        print(f"✅ مواد اولیه: {material_count_after} مورد")
    
    # 3. بررسی میزها
    table_count = Table.query.count()
    if table_count == 0:
        print("\\n🪑 ایجاد میزهای اولیه...")
        # ایجاد یک منطقه
        area = TableArea.query.first()
        if not area:
            area = TableArea(name="سالن اصلی")
            db.session.add(area)
            db.session.commit()
        
        # ایجاد 4 میز
        for i in range(1, 5):
            table = Table(
                number=i,
                capacity=4,
                area_id=area.id,
                is_reserved=False
            )
            db.session.add(table)
        db.session.commit()
        print("✅ 4 میز اولیه ایجاد شد")
    else:
        print(f"\\n✅ میزها: {table_count} عدد")
    
    # خلاصه
    print("\\n" + "="*60)
    print("📊 خلاصه دیتابیس:")
    print("="*60)
    print(f"👤 کاربران: {User.query.count()}")
    print(f"⚙️  تنظیمات: {Settings.query.count()}")
    print(f"📁 دسته‌بندی‌ها: {Category.query.count()}")
    print(f"🍽️  آیتم‌های منو: {MenuItem.query.count()}")
    print(f"👥 مشتریان: {Customer.query.count()}")
    print(f"🪑 میزها: {Table.query.count()}")
    print(f"📦 مواد اولیه: {RawMaterial.query.count()}")
    print(f"💰 خریدهای مواد: {MaterialPurchase.query.count()}")
    print("="*60)
    print("\\n✅ دیتابیس آماده استفاده است!")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD)

print("🔧 در حال تنظیم دیتابیس در سرور...\n")

sftp = ssh.open_sftp()
with sftp.open(f'{REMOTE_PATH}/temp_setup_db.py', 'w') as f:
    f.write(python_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command(f'cd {REMOTE_PATH} && source venv/bin/activate && python3 temp_setup_db.py')
time.sleep(5)

output = stdout.read().decode('utf-8', errors='ignore')
errors = stderr.read().decode('utf-8', errors='ignore')

print(output)
if errors and 'Traceback' in errors:
    print("\n❌ خطا:", errors)

ssh.close()

