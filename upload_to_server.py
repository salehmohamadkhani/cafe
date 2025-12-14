#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت Python برای آپلود فایل‌ها به سرور
"""
import os
import sys
import paramiko
from pathlib import Path

# Ensure stdout/stderr can print Persian text on Windows terminals
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# تنظیمات (از ENV بخوانید تا secret داخل Git نرود)
SERVER_IP = os.environ.get("CAFE_SERVER_IP", "").strip() or "CHANGE_ME"
SERVER_USER = os.environ.get("CAFE_SERVER_USER", "").strip() or "root"
SERVER_PASSWORD = os.environ.get("CAFE_SERVER_PASSWORD", "")
REMOTE_PATH = os.environ.get("CAFE_REMOTE_PATH", "").strip() or "/var/www/کافه"
LOCAL_PATH = Path(__file__).parent

print("شروع آپلود فایل‌ها به سرور...")

# نصب paramiko اگر نصب نیست
try:
    import paramiko
except ImportError:
    print("نصب paramiko...")
    os.system(f"{sys.executable} -m pip install paramiko")
    import paramiko

# ایجاد SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    # اتصال به سرور
    if SERVER_IP == "CHANGE_ME" or not SERVER_PASSWORD:
        raise RuntimeError("CAFE_SERVER_IP و CAFE_SERVER_PASSWORD باید در Environment Variables تنظیم شوند.")
    print("اتصال به سرور...")
    ssh.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASSWORD, timeout=10)
    print("اتصال برقرار شد")
    
    # ایجاد پوشه در سرور
    print("ایجاد پوشه در سرور...")
    stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {REMOTE_PATH}")
    stdout.channel.recv_exit_status()
    print("پوشه ایجاد شد")
    
    # ایجاد SFTP client
    sftp = ssh.open_sftp()
    
    # لیست فایل‌های لازم
    files_to_copy = [
        "app.py",
        "auth.py",
        "config.py",
        "wsgi.py",
        "requirements_production.txt",
        "gunicorn_config.py",
        "nginx_config.conf",
        "systemd_service.txt",
        "deploy_remote.sh"
    ]
    
    folders_to_copy = [
        "templates",
        "static",
        "models",
        "routes",
        "services",
        "utils",
        "migrations",
        "data"
    ]
    
    # کپی فایل‌ها
    print("\nکپی فایل‌ها...")
    for file in files_to_copy:
        local_file = LOCAL_PATH / file
        if local_file.exists():
            print(f"  - {file}")
            remote_file = f"{REMOTE_PATH}/{file}"
            sftp.put(str(local_file), remote_file)
    
    # کپی پوشه‌ها
    print("\nکپی پوشه‌ها...")
    for folder in folders_to_copy:
        local_folder = LOCAL_PATH / folder
        if local_folder.exists():
            print(f"  - {folder}/")
            # ایجاد پوشه در سرور
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {REMOTE_PATH}/{folder}")
            stdout.channel.recv_exit_status()
            
            # کپی تمام فایل‌های داخل پوشه
            for root, dirs, files in os.walk(local_folder):
                for file in files:
                    local_file = Path(root) / file
                    relative_path = local_file.relative_to(LOCAL_PATH)
                    remote_file = f"{REMOTE_PATH}/{str(relative_path).replace(chr(92), '/')}"
                    
                    # ایجاد پوشه والد در سرور
                    remote_dir = os.path.dirname(remote_file)
                    stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                    stdout.channel.recv_exit_status()
                    
                    # کپی فایل
                    sftp.put(str(local_file), remote_file)
    
    sftp.close()
    print("\nتمام فایل‌ها با موفقیت آپلود شدند.")
    
    print("\nحالا می‌توانید اسکریپت deploy_remote.sh را در سرور اجرا کنید:")
    print(f"  ssh {SERVER_USER}@{SERVER_IP}")
    print(f"  cd {REMOTE_PATH}")
    print("  bash deploy_remote.sh")
    
except Exception as e:
    print(f"خطا: {e}")
    sys.exit(1)
finally:
    ssh.close()

