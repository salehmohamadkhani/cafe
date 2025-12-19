#!/usr/bin/env python3
"""
اسکریپت برای خالی کردن کامل دیتابیس
این اسکریپت تمام جداول را پاک می‌کند اما ساختار جداول را حفظ می‌کند
"""

import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import (
    db,
    OrderItem,
    Order,
    TableItem,
    Table,
    Customer,
    MenuItem,
    Category,
    RawMaterialUsage,
    MenuItemMaterial,
    MaterialPurchase,
    WarehouseTransfer,
    SnapSettlement,
    ActionLog,
    RawMaterial,
    Warehouse,
    TableArea,
    Settings,
    CostFormulaSettings,
    User
)

def clear_all_database():
    """خالی کردن تمام جداول دیتابیس"""
    app = create_app()
    with app.app_context():
        try:
            print("🔄 شروع پاک کردن دیتابیس...")
            
            # غیرفعال کردن foreign key constraints (برای SQLite)
            db.session.execute(db.text("PRAGMA foreign_keys = OFF"))
            
            # پاک کردن جداول به ترتیب وابستگی
            print("📦 پاک کردن OrderItem...")
            OrderItem.query.delete()
            
            print("📦 پاک کردن Order...")
            Order.query.delete()
            
            print("📦 پاک کردن TableItem...")
            TableItem.query.delete()
            
            print("📦 پاک کردن RawMaterialUsage...")
            RawMaterialUsage.query.delete()
            
            print("📦 پاک کردن MenuItemMaterial...")
            MenuItemMaterial.query.delete()
            
            print("📦 پاک کردن MaterialPurchase...")
            MaterialPurchase.query.delete()
            
            print("📦 پاک کردن WarehouseTransfer...")
            WarehouseTransfer.query.delete()
            
            print("📦 پاک کردن SnapSettlement...")
            SnapSettlement.query.delete()
            
            print("📦 پاک کردن ActionLog...")
            ActionLog.query.delete()
            
            print("📦 پاک کردن Table...")
            Table.query.delete()
            
            print("📦 پاک کردن Customer...")
            Customer.query.delete()
            
            print("📦 پاک کردن MenuItem...")
            MenuItem.query.delete()
            
            print("📦 پاک کردن Category...")
            Category.query.delete()
            
            print("📦 پاک کردن RawMaterial...")
            RawMaterial.query.delete()
            
            print("📦 پاک کردن Warehouse...")
            Warehouse.query.delete()
            
            print("📦 پاک کردن TableArea...")
            TableArea.query.delete()
            
            print("📦 پاک کردن Settings...")
            Settings.query.delete()
            
            print("📦 پاک کردن CostFormulaSettings...")
            CostFormulaSettings.query.delete()
            
            # User را آخر پاک می‌کنیم (ممکن است foreign key به آن باشد)
            print("📦 پاک کردن User...")
            User.query.delete()
            
            # فعال کردن دوباره foreign key constraints
            db.session.execute(db.text("PRAGMA foreign_keys = ON"))
            
            # commit تغییرات
            db.session.commit()
            
            print("✅ دیتابیس با موفقیت خالی شد!")
            print("📊 تمام جداول پاک شدند اما ساختار جداول حفظ شده است.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطا در پاک کردن دیتابیس: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    import sys
    
    # اگر flag --yes یا --force ارسال شده باشد، بدون سوال اجرا می‌شود
    force = '--yes' in sys.argv or '--force' in sys.argv or '-y' in sys.argv
    
    if not force:
        print("=" * 50)
        print("⚠️  هشدار: این اسکریپت تمام داده‌های دیتابیس را پاک می‌کند!")
        print("=" * 50)
        print("💡 برای اجرای خودکار، از flag --yes استفاده کنید: python clear_all_database.py --yes")
        print("=" * 50)
        
        try:
            response = input("آیا مطمئن هستید که می‌خواهید ادامه دهید؟ (yes/no): ")
            if response.lower() not in ['yes', 'y', 'بله', 'ب']:
                print("❌ عملیات لغو شد.")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\n❌ عملیات لغو شد.")
            sys.exit(0)
    
    clear_all_database()
