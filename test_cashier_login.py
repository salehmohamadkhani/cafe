#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to check cashier user login"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.master_models import CafeTenant
from werkzeug.security import check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import User

def test_cashier_login():
    app = create_app()
    with app.app_context():
        # Get all cafes
        cafes = CafeTenant.query.all()
        print(f"تعداد کافه‌ها: {len(cafes)}\n")
        
        for cafe in cafes:
            print(f"کافه: {cafe.name} (slug: {cafe.slug})")
            print(f"  دیتابیس: {cafe.db_path}")
            
            if not os.path.exists(cafe.db_path):
                print(f"  ❌ دیتابیس وجود ندارد!")
                continue
            
            # Connect to tenant DB
            engine = create_engine(f"sqlite:///{cafe.db_path}")
            Session = sessionmaker(bind=engine)
            
            with Session() as s:
                # Get all users
                users = s.query(User).all()
                print(f"  تعداد کاربران: {len(users)}")
                
                for user in users:
                    print(f"\n  کاربر: {user.username}")
                    print(f"    نقش: {user.role}")
                    print(f"    فعال: {user.is_active}")
                    print(f"    نام: {user.name or '-'}")
                    print(f"    تلفن: {user.phone or '-'}")
                    print(f"    password_hash: {user.password_hash[:50]}...")
                    
                    # Test with common passwords
                    test_passwords = ['123456', '123', 'password', 'admin', 'cashier']
                    for test_pwd in test_passwords:
                        if check_password_hash(user.password_hash, test_pwd):
                            print(f"    ✅ رمز عبور: '{test_pwd}'")
                            break
                    else:
                        print(f"    ❌ رمز عبور تست نشد (رمزهای تست شده: {', '.join(test_passwords)})")
            
            print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_cashier_login()

