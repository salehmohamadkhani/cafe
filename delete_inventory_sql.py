"""
حذف مستقیم داده‌های انبار با SQL خام
این اسکریپت مستقیماً به دیتابیس SQLite وصل می‌شود و با SQL داده‌ها را حذف می‌کند
"""

import sqlite3
import os
import sys
import io

# تنظیم encoding برای stdout
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# مسیر دیتابیس
BASEDIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASEDIR, 'instance')
db_path = os.path.join(INSTANCE_DIR, 'cafe.db')

if not os.path.exists(db_path):
    print(f"خطا: فایل دیتابیس یافت نشد: {db_path}")
    exit(1)

print(f"اتصال به دیتابیس: {db_path}")
print("=" * 50)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # شمارش رکوردها قبل از حذف
    print("\nشمارش رکوردهای موجود:")
    
    cursor.execute("SELECT COUNT(*) FROM raw_material_usage")
    usage_count = cursor.fetchone()[0]
    print(f"  - مصرف مواد اولیه: {usage_count}")
    
    cursor.execute("SELECT COUNT(*) FROM warehouse_transfer")
    transfer_count = cursor.fetchone()[0]
    print(f"  - انتقال‌های بین انبارها: {transfer_count}")
    
    cursor.execute("SELECT COUNT(*) FROM material_purchase")
    purchase_count = cursor.fetchone()[0]
    print(f"  - خریدهای مواد اولیه: {purchase_count}")
    
    cursor.execute("SELECT COUNT(*) FROM menu_item_material")
    menu_material_count = cursor.fetchone()[0]
    print(f"  - ارتباط مواد اولیه با آیتم‌های منو: {menu_material_count}")
    
    cursor.execute("SELECT COUNT(*) FROM raw_material")
    raw_material_count = cursor.fetchone()[0]
    print(f"  - مواد اولیه: {raw_material_count}")
    
    # حذف داده‌ها با SQL
    print("\nدر حال حذف با SQL...")
    
    # 1. حذف مصرف مواد اولیه
    cursor.execute("DELETE FROM raw_material_usage")
    print(f"  ✓ مصرف مواد اولیه حذف شد ({cursor.rowcount} رکورد)")
    
    # 2. حذف انتقال‌های بین انبارها
    cursor.execute("DELETE FROM warehouse_transfer")
    print(f"  ✓ انتقال‌های بین انبارها حذف شد ({cursor.rowcount} رکورد)")
    
    # 3. حذف خریدهای مواد اولیه
    cursor.execute("DELETE FROM material_purchase")
    print(f"  ✓ خریدهای مواد اولیه حذف شد ({cursor.rowcount} رکورد)")
    
    # 4. حذف ارتباط مواد اولیه با آیتم‌های منو
    cursor.execute("DELETE FROM menu_item_material")
    print(f"  ✓ ارتباط مواد اولیه با آیتم‌های منو حذف شد ({cursor.rowcount} رکورد)")
    
    # 5. حذف مواد اولیه
    cursor.execute("DELETE FROM raw_material")
    print(f"  ✓ مواد اولیه حذف شد ({cursor.rowcount} رکورد)")
    
    # Commit تغییرات
    conn.commit()
    
    # بررسی نهایی
    print("\nبررسی نهایی:")
    cursor.execute("SELECT COUNT(*) FROM raw_material")
    remaining = cursor.fetchone()[0]
    
    if remaining == 0:
        print("✓ تمام داده‌های انبار با موفقیت حذف شدند!")
    else:
        print(f"⚠ هشدار: {remaining} رکورد مواد اولیه باقی مانده است!")
    
    cursor.close()
    conn.close()
    
except sqlite3.Error as e:
    print(f"\n✗ خطای SQLite: {str(e)}")
    if conn:
        conn.rollback()
        conn.close()
    exit(1)
except Exception as e:
    print(f"\n✗ خطا: {str(e)}")
    if conn:
        conn.rollback()
        conn.close()
    exit(1)
