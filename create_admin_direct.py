#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ایجاد کاربر ادمین - اجرای مستقیم"""
import os
import paramiko
import base64

SERVER_IP = os.environ.get("CAFE_SERVER_IP", "").strip()
SERVER_USER = os.environ.get("CAFE_SERVER_USER", "root").strip() or "root"
SERVER_PASSWORD = os.environ.get("CAFE_SERVER_PASSWORD", "")
REMOTE_PATH = os.environ.get("CAFE_REMOTE_PATH", "/var/www/کافه").strip() or "/var/www/کافه"

if not SERVER_IP or not SERVER_PASSWORD:
    raise RuntimeError("CAFE_SERVER_IP و CAFE_SERVER_PASSWORD باید در Environment Variables تنظیم شوند.")

# کد Python برای اجرا در سرور
python_code = '''
import sys
import os
sys.path.insert(0, "/var/www/کافه")

from app import create_app
from models.models import User, db
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # بررسی وجود کاربر
    existing = User.query.first()
    if existing:
        print(f"⚠️  کاربر موجود: Username={existing.username}, Name={existing.name}")
    else:
        # ایجاد کاربر ادمین
        admin = User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            name="مدیر سیستم",
            phone="",
            role="admin",
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ کاربر ادمین ایجاد شد!")
        print("Username: admin")
        print("Password: admin123")
        print("Name: مدیر سیستم")
    
    # نمایش همه کاربران
    users = User.query.all()
    print(f"\\n📊 تعداد کاربران: {len(users)}")
    for u in users:
        print(f"  - {u.username} ({u.name}) - {u.role}")
'''

# اتصال به سرور
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD)

# اجرای کد
print("🔧 در حال ایجاد کاربر ادمین...\n")
command = f'cd {REMOTE_PATH} && source venv/bin/activate && python3 -c {repr(python_code)}'
stdin, stdout, stderr = ssh.exec_command(command)

import time
time.sleep(3)

output = stdout.read().decode('utf-8', errors='ignore')
errors = stderr.read().decode('utf-8', errors='ignore')

print(output)
if errors:
    print("\n⚠️  خطاها:", errors)

ssh.close()

