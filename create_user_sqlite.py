#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ایجاد کاربر از طریق SQLite مستقیم"""
import os
import paramiko
import time

SERVER_IP = os.environ.get("CAFE_SERVER_IP", "").strip()
SERVER_USER = os.environ.get("CAFE_SERVER_USER", "root").strip() or "root"
SERVER_PASSWORD = os.environ.get("CAFE_SERVER_PASSWORD", "")
REMOTE_PATH = os.environ.get("CAFE_REMOTE_PATH", "/var/www/کافه").strip() or "/var/www/کافه"

if not SERVER_IP or not SERVER_PASSWORD:
    raise RuntimeError("CAFE_SERVER_IP و CAFE_SERVER_PASSWORD باید در Environment Variables تنظیم شوند.")

# کد Python برای اجرا
python_code = '''import sys
sys.path.insert(0, "/var/www/کافه")
from app import create_app
from models.models import User, db
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # بررسی وجود کاربر
    existing = User.query.first()
    if existing:
        print(f"⚠️  کاربر موجود: {existing.username} ({existing.name})")
    else:
        # ایجاد کاربر
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
        print("✅ کاربر ایجاد شد!")
    
    # نمایش همه
    users = User.query.all()
    print(f"\\n📊 تعداد: {len(users)}")
    for u in users:
        print(f"  Username: {u.username}")
        print(f"  Name: {u.name}")
        print(f"  Role: {u.role}")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD)

print("🔧 ایجاد کاربر...\n")

# نوشتن کد در فایل موقت
sftp = ssh.open_sftp()
with sftp.open(f'{REMOTE_PATH}/temp_create_user.py', 'w') as f:
    f.write(python_code)
sftp.close()

# اجرا
stdin, stdout, stderr = ssh.exec_command(f'cd {REMOTE_PATH} && source venv/bin/activate && python3 temp_create_user.py')
time.sleep(4)

output = stdout.read().decode('utf-8', errors='ignore')
errors = stderr.read().decode('utf-8', errors='ignore')

print(output)
if errors:
    print("خطاها:", errors)

ssh.close()

