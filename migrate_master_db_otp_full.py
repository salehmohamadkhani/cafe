#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration کامل برای تغییر password_hash به nullable
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
            return
        
        conn = sqlite3.connect(master_db_path)
        cursor = conn.cursor()
        
        try:
            # بررسی constraint فعلی
            cursor.execute("PRAGMA table_info(master_user)")
            columns_info = cursor.fetchall()
            password_hash_col = next((col for col in columns_info if col[1] == 'password_hash'), None)
            
            if password_hash_col and password_hash_col[3] == 1:  # NOT NULL
                print("➕ تغییر password_hash به nullable...")
                
                # بازسازی جدول
                cursor.execute("""
                    CREATE TABLE master_user_new (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(64),
                        phone_number VARCHAR(20) NOT NULL,
                        password_hash VARCHAR(256),
                        role VARCHAR(32) NOT NULL DEFAULT 'superadmin',
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_login DATETIME
                    )
                """)
                
                # کپی داده‌ها
                cursor.execute("""
                    INSERT INTO master_user_new 
                    (id, username, phone_number, password_hash, role, is_active, created_at, last_login)
                    SELECT 
                        id, 
                        username, 
                        COALESCE(phone_number, username, ''),
                        password_hash,
                        role,
                        is_active,
                        created_at,
                        last_login
                    FROM master_user
                """)
                
                # حذف جدول قدیمی و تغییر نام
                cursor.execute("DROP TABLE master_user")
                cursor.execute("ALTER TABLE master_user_new RENAME TO master_user")
                
                # ایجاد index ها
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_master_user_username ON master_user(username)")
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_master_user_phone_number ON master_user(phone_number)")
                
                print("✅ password_hash به nullable تغییر یافت.")
            else:
                print("✅ password_hash از قبل nullable است.")
            
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

