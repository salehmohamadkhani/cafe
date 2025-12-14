#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تقسیم آیتم‌های موجود به 4 دسته‌بندی"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import Category, MenuItem, db

app = create_app()
with app.app_context():
    # دریافت همه آیتم‌های فعال
    all_items = MenuItem.query.filter_by(is_active=True).all()
    
    # دریافت یا ایجاد 4 دسته‌بندی
    categories = []
    category_names = [
        "نوشیدنی‌های گرم",
        "نوشیدنی‌های سرد",
        "دسر و شیرینی",
        "غذا و اسنک"
    ]
    
    for i, cat_name in enumerate(category_names):
        category = Category.query.filter_by(name=cat_name).first()
        if not category:
            category = Category(
                name=cat_name,
                description=f"دسته‌بندی {cat_name}",
                order=i,
                is_active=True
            )
            db.session.add(category)
            db.session.flush()
        categories.append(category)
    
    db.session.commit()
    
    # تقسیم آیتم‌ها به 4 دسته‌بندی (به صورت مساوی)
    items_per_category = len(all_items) // 4
    remainder = len(all_items) % 4
    
    start_idx = 0
    for i, category in enumerate(categories):
        end_idx = start_idx + items_per_category + (1 if i < remainder else 0)
        items_for_category = all_items[start_idx:end_idx]
        
        for item in items_for_category:
            item.category_id = category.id
        
        print(f"✅ {category.name}: {len(items_for_category)} آیتم")
        start_idx = end_idx
    
    db.session.commit()
    
    print(f"\n✅ {len(all_items)} آیتم به 4 دسته‌بندی تقسیم شدند!")

