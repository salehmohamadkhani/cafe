#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a cashier user in tenant database"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.master_models import CafeTenant
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import User
from datetime import datetime
import pytz

def create_cashier():
    app = create_app()
    with app.app_context():
        # Get all cafes
        cafes = CafeTenant.query.all()
        
        if not cafes:
            print("❌ هیچ کافه‌ای یافت نشد!")
            return
        
        print("کافه‌های موجود:")
        for i, cafe in enumerate(cafes, 1):
            print(f"  {i}. {cafe.name} (slug: {cafe.slug})")
        
        if len(cafes) == 1:
            cafe = cafes[0]
            print(f"\n✅ استفاده از کافه: {cafe.name}")
        else:
            choice = input("\nشماره کافه را انتخاب کنید: ").strip()
            try:
                cafe = cafes[int(choice) - 1]
            except (ValueError, IndexError):
                print("❌ انتخاب نامعتبر!")
                return
        
        # Get username and password
        username = input("\nنام کاربری: ").strip()
        if not username:
            print("❌ نام کاربری الزامی است!")
            return
        
        password = input("رمز عبور: ").strip()
        if not password:
            print("❌ رمز عبور الزامی است!")
            return
        
        if len(password) < 6:
            print("❌ رمز عبور باید حداقل ۶ کاراکتر باشد!")
            return
        
        # Check if database exists
        if not os.path.exists(cafe.db_path):
            print(f"❌ دیتابیس یافت نشد: {cafe.db_path}")
            return
        
        # Connect to tenant DB
        engine = create_engine(f"sqlite:///{cafe.db_path}")
        Session = sessionmaker(bind=engine)
        
        with Session() as s:
            # Check if user already exists
            existing = s.query(User).filter_by(username=username).first()
            if existing:
                print(f"❌ کاربر '{username}' قبلاً وجود دارد!")
                update = input("آیا می‌خواهید رمز عبور را تغییر دهید؟ (y/n): ").strip().lower()
                if update == 'y':
                    existing.password_hash = generate_password_hash(password)
                    existing.role = 'cashier'
                    s.commit()
                    print(f"✅ رمز عبور کاربر '{username}' تغییر یافت و نقش به 'cashier' تنظیم شد.")
                return
            
            # Create new user
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                name=input("نام و نام خانوادگی (اختیاری): ").strip() or None,
                role='cashier',
                phone=input("شماره تماس (اختیاری): ").strip() or None,
                created_at=datetime.now(pytz.timezone("Asia/Tehran")),
                is_active=True
            )
            s.add(user)
            s.commit()
            
            print(f"\n✅ کاربر '{username}' با نقش 'cashier' با موفقیت ایجاد شد!")
            print(f"   رمز عبور: {password}")
            print(f"   کافه: {cafe.name}")

if __name__ == "__main__":
    create_cashier()

