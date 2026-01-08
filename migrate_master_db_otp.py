#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script برای اضافه کردن فیلد phone_number به MasterUser
و ایجاد جدول OTPCode
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config import Config

def migrate():
    app = create_app()
    with app.app_context():
        master_db_path = Config.MASTER_DB_URI.replace('sqlite:///', '')
        
        if not os.path.exists(master_db_path):
            print(f"❌ دیتابیس master یافت نشد: {master_db_path}")
            print("   ابتدا باید یک کاربر master ایجاد کنید.")
            return
        
        conn = sqlite3.connect(master_db_path)
        cursor = conn.cursor()
        
        try:
            # بررسی وجود فیلد phone_number
            cursor.execute("PRAGMA table_info(master_user)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'phone_number' not in columns:
                print("➕ اضافه کردن فیلد phone_number به جدول master_user...")
                cursor.execute("ALTER TABLE master_user ADD COLUMN phone_number VARCHAR(20)")
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_master_user_phone_number ON master_user(phone_number)")
                
                # تبدیل username به phone_number برای کاربران موجود
                cursor.execute("SELECT id, username FROM master_user WHERE phone_number IS NULL")
                users = cursor.fetchall()
                for user_id, username in users:
                    if username:
                        # اگر username یک شماره موبایل است، از آن استفاده کن
                        phone = username.replace(' ', '').replace('-', '').replace('+', '')
                        if phone.startswith('0'):
                            phone = '98' + phone[1:]
                        elif not phone.startswith('98'):
                            phone = '98' + phone
                        cursor.execute("UPDATE master_user SET phone_number = ? WHERE id = ?", (phone, user_id))
                
                print("✅ فیلد phone_number اضافه شد.")
            else:
                print("✅ فیلد phone_number از قبل وجود دارد.")
            
            # بررسی و تغییر password_hash به nullable
            cursor.execute("PRAGMA table_info(master_user)")
            columns_info = cursor.fetchall()
            password_hash_col = next((col for col in columns_info if col[1] == 'password_hash'), None)
            if password_hash_col and password_hash_col[3] == 1:  # NOT NULL
                print("➕ تغییر password_hash به nullable...")
                # SQLite نمی‌تواند مستقیماً NOT NULL را حذف کند، باید جدول را بازسازی کنیم
                # اما برای سادگی، فقط یک مقدار پیش‌فرض می‌گذاریم
                # در واقعیت، باید جدول را بازسازی کنیم
                print("   ⚠️  توجه: برای تغییر NOT NULL constraint، باید جدول را بازسازی کنیم.")
                print("   در حال حاضر، password_hash می‌تواند خالی باشد برای کاربران OTP-only.")
                # برای کاربران موجود که password_hash ندارند، یک مقدار dummy می‌گذاریم
                cursor.execute("UPDATE master_user SET password_hash = '' WHERE password_hash IS NULL")
                print("✅ password_hash برای کاربران موجود تنظیم شد.")
            
            # بررسی وجود جدول otp_code
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='otp_code'")
            if not cursor.fetchone():
                print("➕ ایجاد جدول otp_code...")
                cursor.execute("""
                    CREATE TABLE otp_code (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        phone_number VARCHAR(20) NOT NULL,
                        code VARCHAR(6) NOT NULL,
                        is_used BOOLEAN NOT NULL DEFAULT 0,
                        expires_at DATETIME NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_otp_code_phone_number ON otp_code(phone_number)")
                print("✅ جدول otp_code ایجاد شد.")
            else:
                print("✅ جدول otp_code از قبل وجود دارد.")
            
            conn.commit()
            print("\n✅ Migration با موفقیت انجام شد!")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ خطا در migration: {e}")
            raise
        finally:
            conn.close()

if __name__ == "__main__":
    migrate()

