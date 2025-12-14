#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ایجاد کاربر در سرور"""
import os
import paramiko

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
sftp = ssh.open_sftp()
sftp.put('create_admin_user.py', f'{REMOTE_PATH}/create_admin_user.py')
sftp.close()

# اجرای اسکریپت
print("🔧 در حال ایجاد کاربر ادمین...\n")
stdin, stdout, stderr = ssh.exec_command(f'cd {REMOTE_PATH} && source venv/bin/activate && python create_admin_user.py')

output = ''.join(stdout.readlines())
errors = ''.join(stderr.readlines())

print(output)
if errors and 'Traceback' in errors:
    print("❌ خطا:", errors)

ssh.close()

