#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ایجاد کاربر ادمین در سرور - روش نهایی"""
import os
import paramiko
import time

SERVER_IP = os.environ.get("CAFE_SERVER_IP", "").strip()
SERVER_USER = os.environ.get("CAFE_SERVER_USER", "root").strip() or "root"
SERVER_PASSWORD = os.environ.get("CAFE_SERVER_PASSWORD", "")
REMOTE_PATH = os.environ.get("CAFE_REMOTE_PATH", "/var/www/کافه").strip() or "/var/www/کافه"

if not SERVER_IP or not SERVER_PASSWORD:
    raise RuntimeError("CAFE_SERVER_IP و CAFE_SERVER_PASSWORD باید در Environment Variables تنظیم شوند.")

# اتصال به سرور
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD)

# کپی فایل create_admin_user.py
print("📤 آپلود فایل create_admin_user.py...")
sftp = ssh.open_sftp()
sftp.put('create_admin_user.py', f'{REMOTE_PATH}/create_admin_user.py')
sftp.close()
print("✅ فایل آپلود شد\n")

# اجرای اسکریپت با bash
print("🔧 در حال ایجاد کاربر ادمین...\n")
command = f'bash -c "cd {REMOTE_PATH} && source venv/bin/activate && python3 create_admin_user.py"'
stdin, stdout, stderr = ssh.exec_command(command)

# صبر برای اجرا
time.sleep(5)

# خواندن خروجی
output = stdout.read().decode('utf-8', errors='ignore')
errors = stderr.read().decode('utf-8', errors='ignore')

if output:
    print(output)
if errors and 'Traceback' in errors:
    print("\n❌ خطا:", errors)
elif errors:
    print("\n⚠️  هشدار:", errors)

# بررسی مجدد
print("\n" + "="*60)
print("بررسی مجدد کاربران:")
print("="*60)
stdin, stdout, stderr = ssh.exec_command(f'cd {REMOTE_PATH} && source venv/bin/activate && python3 check_users.py')
time.sleep(3)
output2 = stdout.read().decode('utf-8', errors='ignore')
print(output2)

ssh.close()

