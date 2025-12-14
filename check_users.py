#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسی کاربران در دیتابیس"""
import sys
import os

# اضافه کردن مسیر پروژه
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import User

app = create_app()
with app.app_context():
    users = User.query.all()
    
    print("\n" + "="*60)
    print("لیست کاربران موجود در دیتابیس:")
    print("="*60)
    
    if not users:
        print("❌ هیچ کاربری در دیتابیس وجود ندارد!")
        print("\n💡 برای ایجاد کاربر جدید:")
        print("   - از صفحه register استفاده کنید")
        print("   - یا از طریق Python shell یک کاربر ایجاد کنید")
    else:
        for u in users:
            print(f"\n👤 ID: {u.id}")
            print(f"   Username: {u.username}")
            print(f"   Name: {u.name or '(خالی)'}")
            print(f"   Phone: {u.phone or '(خالی)'}")
            print(f"   Role: {u.role}")
            print(f"   Active: {'✅' if u.is_active else '❌'}")
            print("-" * 60)
    
    print(f"\n📊 تعداد کل کاربران: {len(users)}")
    print("="*60 + "\n")

