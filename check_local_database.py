#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسی داده‌های دیتابیس محلی"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import *

app = create_app()
with app.app_context():
    print("="*60)
    print("📊 داده‌های دیتابیس محلی:")
    print("="*60)
    
    print(f"👤 کاربران: {User.query.count()}")
    print(f"⚙️  تنظیمات: {Settings.query.count()}")
    print(f"📁 دسته‌بندی‌ها: {Category.query.count()}")
    print(f"🍽️  آیتم‌های منو: {MenuItem.query.count()}")
    print(f"👥 مشتریان: {Customer.query.count()}")
    print(f"🪑 میزها: {Table.query.count()}")
    print(f"📦 مواد اولیه: {RawMaterial.query.count()}")
    print(f"💰 خریدهای مواد: {MaterialPurchase.query.count()}")
    print(f"📋 سفارش‌ها: {Order.query.count()}")
    
    # نمایش دسته‌بندی‌ها
    categories = Category.query.all()
    if categories:
        print(f"\\n📁 دسته‌بندی‌ها:")
        for cat in categories:
            print(f"  - {cat.name} ({MenuItem.query.filter_by(category_id=cat.id).count()} آیتم)")
    
    # نمایش چند آیتم منو
    menu_items = MenuItem.query.limit(5).all()
    if menu_items:
        print(f"\\n🍽️  نمونه آیتم‌های منو:")
        for item in menu_items:
            print(f"  - {item.name} ({item.price})")
    
    print("="*60)

