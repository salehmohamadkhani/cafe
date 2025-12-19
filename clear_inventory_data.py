"""
اسکریپت حذف تمام داده‌های انبار
این اسکریپت تمام داده‌های مربوط به انبار را از دیتابیس حذف می‌کند:
- مواد اولیه (RawMaterial)
- خریدهای مواد اولیه (MaterialPurchase)
- انتقال‌های بین انبارها (WarehouseTransfer)
- مصرف مواد اولیه (RawMaterialUsage)
- ارتباط مواد اولیه با آیتم‌های منو (MenuItemMaterial)
"""

from app import create_app
from models.models import db, RawMaterial, MaterialPurchase, WarehouseTransfer, RawMaterialUsage, MenuItemMaterial

app = create_app()

with app.app_context():
    print("شروع حذف داده‌های انبار...")
    
    try:
        # شمارش رکوردها قبل از حذف
        raw_material_count = RawMaterial.query.count()
        purchase_count = MaterialPurchase.query.count()
        transfer_count = WarehouseTransfer.query.count()
        usage_count = RawMaterialUsage.query.count()
        menu_material_count = MenuItemMaterial.query.count()
        
        print(f"\nتعداد رکوردهای موجود:")
        print(f"  - مواد اولیه: {raw_material_count}")
        print(f"  - خریدها: {purchase_count}")
        print(f"  - انتقال‌ها: {transfer_count}")
        print(f"  - مصرف‌ها: {usage_count}")
        print(f"  - مواد آیتم‌های منو: {menu_material_count}")
        
        # حذف داده‌ها
        print("\nدر حال حذف...")
        
        RawMaterialUsage.query.delete()
        print("  ✓ مصرف مواد اولیه حذف شد")
        
        WarehouseTransfer.query.delete()
        print("  ✓ انتقال‌های بین انبارها حذف شد")
        
        MaterialPurchase.query.delete()
        print("  ✓ خریدهای مواد اولیه حذف شد")
        
        MenuItemMaterial.query.delete()
        print("  ✓ ارتباط مواد اولیه با آیتم‌های منو حذف شد")
        
        RawMaterial.query.delete()
        print("  ✓ مواد اولیه حذف شد")
        
        db.session.commit()
        
        print("\n✓ تمام داده‌های انبار با موفقیت حذف شدند!")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n✗ خطا در حذف داده‌ها: {str(e)}")
        raise
