#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ایجاد کاربر ادمین اولیه"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import User, db
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    # بررسی وجود کاربر
    existing = User.query.first()
    if existing:
        print("⚠️  کاربری در دیتابیس وجود دارد:")
        print(f"   Username: {existing.username}")
        print(f"   Name: {existing.name}")
        # ایجاد کاربر ادمین
        username = "admin"
        password = "admin123"  # باید بعداً تغییر دهید!
        name = "مدیر سیستم"
        phone = ""
        role = "admin"
        
        admin = User(
            username=username,
            password_hash=generate_password_hash(password),
            name=name,
            phone=phone,
            role=role,
            is_active=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ کاربر ادمین با موفقیت ایجاد شد!")
        print("\n" + "="*60)
        print("اطلاعات ورود:")
        print("="*60)
        print(f"👤 Username: {username}")
        print(f"🔑 Password: {password}")
        print(f"📛 Name: {name}")
        print(f"👔 Role: {role}")
        print("="*60)
        print("\n⚠️  مهم: لطفاً بعد از ورود، رمز عبور را تغییر دهید!")
        print("="*60 + "\n")

