"""
اسکریپت برای ایجاد انبار پیش تولید
"""
import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import db, Warehouse

def create_pre_production_warehouse():
    """ایجاد انبار پیش تولید اگر وجود نداشته باشد"""
    app = create_app()
    with app.app_context():
        # بررسی وجود انبار
        existing = Warehouse.query.filter_by(code='pre_production').first()
        if existing:
            print(f"انبار پیش تولید از قبل وجود دارد: {existing.name} (ID: {existing.id})")
            return
        
        # ایجاد انبار جدید
        warehouse = Warehouse(
            code='pre_production',
            name='انبار پیش تولید',
            is_active=True
        )
        db.session.add(warehouse)
        db.session.commit()
        print(f"انبار پیش تولید با موفقیت ایجاد شد: {warehouse.name} (ID: {warehouse.id})")

if __name__ == '__main__':
    create_pre_production_warehouse()

