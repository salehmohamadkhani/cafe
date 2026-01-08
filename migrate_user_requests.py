#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migration script to create user_creation_request table"""

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
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_creation_request'")
            if cursor.fetchone():
                print("✅ جدول user_creation_request از قبل وجود دارد.")
            else:
                print("➕ ایجاد جدول user_creation_request...")
                cursor.execute("""
                    CREATE TABLE user_creation_request (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        cafe_id INTEGER NOT NULL,
                        requested_by VARCHAR(128),
                        username VARCHAR(64) NOT NULL,
                        name VARCHAR(128),
                        phone VARCHAR(20),
                        role VARCHAR(32) NOT NULL DEFAULT 'cashier',
                        status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        generated_username VARCHAR(64),
                        generated_password VARCHAR(128),
                        approved_by INTEGER,
                        approved_at DATETIME,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        notes TEXT,
                        FOREIGN KEY(cafe_id) REFERENCES cafe_tenant(id),
                        FOREIGN KEY(approved_by) REFERENCES master_user(id)
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_creation_request_cafe_id ON user_creation_request(cafe_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_creation_request_status ON user_creation_request(status)")
                print("✅ جدول user_creation_request ایجاد شد.")

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

