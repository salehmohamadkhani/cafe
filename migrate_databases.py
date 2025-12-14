"""
اسکریپت مهاجرت دیتابیس‌ها
این اسکریپت دیتابیس cafe1 را با cafe ادغام می‌کند:
1. داده‌های cafe تا پایان فروردین (ماه 3) را نگه می‌دارد
2. داده‌های بعد از فروردین را از cafe حذف می‌کند
3. تمام داده‌های cafe1 را به cafe منتقل می‌کند
4. دیتابیس cafe1 را حذف می‌کند
"""

import os
import sys
import sqlite3
from datetime import datetime
import pytz
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import shutil

# تنظیم encoding برای Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# مسیر دیتابیس‌ها
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CAFE_DB = os.path.join(BASE_DIR, 'instance', 'cafe.db')
CAFE1_DB = os.path.join(BASE_DIR, 'instance', 'cafe1.db')

iran_tz = pytz.timezone("Asia/Tehran")

def quote_identifier(identifier: str) -> str:
    """محصور کردن نام جداول/ستون‌ها برای جلوگیری از برخورد با کلمات رزرو شده"""
    return f'"{identifier}"'

def get_tables():
    """لیست تمام جداول دیتابیس"""
    return [
        'category',
        'menu_item',
        'customer',
        'order',
        'order_item',
        'settings',
        'user',
        'table',
        'table_item',
        'action_log',
        'menu_item_material',
        'raw_material',
        'material_purchase'
    ]

def get_foreign_key_tables():
    """جداولی که به جداول دیگر وابستگی دارند (باید بعد از جداول اصلی منتقل شوند)"""
    return {
        'order': ['order_item'],
        'menu_item': ['menu_item_material', 'order_item', 'table_item'],
        'customer': ['order'],
        'category': ['menu_item'],
        'user': ['order', 'action_log'],
        'table': ['order', 'table_item'],
        'raw_material': ['menu_item_material', 'material_purchase'],
    }

def delete_data_after_march(cafe_conn):
    """حذف داده‌های بعد از پایان فروردین (31 مارس) از دیتابیس cafe"""
    print("\n=== حذف داده‌های بعد از فروردین از دیتابیس cafe ===")
    
    # تاریخ پایان فروردین (31 مارس) - استفاده از سال جاری
    # اگر می‌خواهید سال خاصی را استفاده کنید، می‌توانید تغییر دهید
    current_year = datetime.now().year
    march_end = datetime(current_year, 3, 31, 23, 59, 59)
    march_end = iran_tz.localize(march_end)
    
    # تبدیل به UTC برای مقایسه
    march_end_utc = march_end.astimezone(pytz.UTC)
    march_end_str = march_end_utc.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"حذف داده‌های بعد از: {march_end.strftime('%Y-%m-%d %H:%M:%S')} (تهران)")
    
    cursor = cafe_conn.cursor()
    
    # ابتدا حذف order_item های مرتبط با order های حذف شده
    # سپس حذف order ها
    try:
        # حذف order های بعد از فروردین
        cursor.execute(f"""
            DELETE FROM {quote_identifier('order')} 
            WHERE datetime(created_at) > datetime(?)
        """, (march_end_str,))
        deleted_orders = cursor.rowcount
        if deleted_orders > 0:
            print(f"  ✓ order: {deleted_orders} سفارش حذف شد")
        
        # حذف order_item های بدون order
        cursor.execute(f"""
            DELETE FROM {quote_identifier('order_item')} 
            WHERE order_id NOT IN (SELECT id FROM {quote_identifier('order')})
        """)
        deleted_order_items = cursor.rowcount
        if deleted_order_items > 0:
            print(f"  ✓ order_item: {deleted_order_items} آیتم سفارش حذف شد")
    except Exception as e:
        print(f"  ✗ خطا در حذف order/order_item: {e}")
    
    # جداول دیگر با فیلد created_at
    other_tables = ['customer', 'category', 'menu_item', 'user', 'table', 
                    'table_item', 'action_log', 'menu_item_material', 
                    'raw_material', 'material_purchase']
    
    for table in other_tables:
        try:
            # بررسی وجود جدول
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                continue
            
            # بررسی وجود فیلد created_at
            cursor.execute(f"PRAGMA table_info({quote_identifier(table)})")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'created_at' in columns:
                # حذف رکوردهای بعد از فروردین
                cursor.execute(f"""
                    DELETE FROM {quote_identifier(table)} 
                    WHERE datetime(created_at) > datetime(?)
                """, (march_end_str,))
                deleted = cursor.rowcount
                if deleted > 0:
                    print(f"  ✓ {table}: {deleted} رکورد حذف شد")
        except Exception as e:
            print(f"  ✗ خطا در حذف از {table}: {e}")
    
    cafe_conn.commit()
    print("✓ حذف داده‌های بعد از فروردین انجام شد\n")

def get_max_id(cafe_conn, table):
    """دریافت بیشترین ID از جدول در دیتابیس cafe"""
    cursor = cafe_conn.cursor()
    try:
        cursor.execute(f"SELECT MAX(id) FROM {quote_identifier(table)}")
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0
    except:
        return 0

def migrate_table(cafe_conn, cafe1_conn, table_name, id_offset=0, foreign_key_mappings=None):
    """انتقال داده‌های یک جدول از cafe1 به cafe و برگرداندن mapping ID ها
    
    Args:
        cafe_conn: اتصال به دیتابیس cafe
        cafe1_conn: اتصال به دیتابیس cafe1
        table_name: نام جدول
        id_offset: offset برای ID ها
        foreign_key_mappings: dictionary از ID mappings برای جداول دیگر {table_name: {old_id: new_id}}
    """
    cursor_cafe = cafe_conn.cursor()
    cursor_cafe1 = cafe1_conn.cursor()
    id_mapping = {}  # old_id -> new_id
    
    if foreign_key_mappings is None:
        foreign_key_mappings = {}
    
    try:
        # بررسی وجود جدول در هر دو دیتابیس
        cursor_cafe.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor_cafe.fetchone():
            print(f"  ⚠ جدول {table_name} در cafe وجود ندارد، رد می‌شود")
            return 0, id_mapping
        
        cursor_cafe1.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor_cafe1.fetchone():
            print(f"  ⚠ جدول {table_name} در cafe1 وجود ندارد، رد می‌شود")
            return 0, id_mapping
        
        # دریافت ساختار جدول
        cursor_cafe.execute(f"PRAGMA table_info({quote_identifier(table_name)})")
        cafe_columns = {col[1]: col for col in cursor_cafe.fetchall()}
        
        cursor_cafe1.execute(f"PRAGMA table_info({quote_identifier(table_name)})")
        cafe1_columns = {col[1]: col for col in cursor_cafe1.fetchall()}
        
        # فقط ستون‌های مشترک
        common_columns = [col for col in cafe_columns.keys() if col in cafe1_columns.keys()]
        
        if not common_columns:
            print(f"  ⚠ هیچ ستون مشترکی در {table_name} پیدا نشد")
            return 0, id_mapping
        
        # دریافت تمام داده‌ها از cafe1
        select_columns = ', '.join(quote_identifier(col) for col in common_columns)
        cursor_cafe1.execute(f"SELECT {select_columns} FROM {quote_identifier(table_name)}")
        rows = cursor_cafe1.fetchall()
        
        if not rows:
            print(f"  - {table_name}: هیچ داده‌ای برای انتقال وجود ندارد")
            return 0, id_mapping
        
        # دریافت بیشترین ID فعلی در cafe
        max_id = get_max_id(cafe_conn, table_name)
        
        migrated_count = 0
        
        for row in rows:
            try:
                # ساخت dictionary از داده‌ها
                row_dict = dict(zip(common_columns, row))
                old_id = None
                
                # اگر id وجود دارد، باید آن را تغییر دهیم
                if 'id' in row_dict and row_dict['id'] is not None:
                    old_id = row_dict['id']
                    # استفاده از offset برای جلوگیری از تداخل ID
                    new_id = old_id + id_offset
                    # اگر هنوز تداخل دارد، از max_id استفاده می‌کنیم
                    if new_id <= max_id:
                        max_id += 1
                        new_id = max_id
                    else:
                        max_id = new_id
                    row_dict['id'] = new_id
                    id_mapping[old_id] = new_id
                
                # به‌روزرسانی foreign key ها بر اساس mappings
                # mapping foreign keys: order_id -> order, customer_id -> customer, etc.
                fk_mappings = {
                    'order_id': 'order',
                    'customer_id': 'customer',
                    'user_id': 'user',
                    'table_id': 'table',
                    'menu_item_id': 'menu_item',
                    'category_id': 'category',
                    'raw_material_id': 'raw_material',
                }
                
                for fk_col, ref_table in fk_mappings.items():
                    if fk_col in row_dict and row_dict[fk_col] is not None:
                        old_fk_id = row_dict[fk_col]
                        if ref_table in foreign_key_mappings and old_fk_id in foreign_key_mappings[ref_table]:
                            row_dict[fk_col] = foreign_key_mappings[ref_table][old_fk_id]
                
                # ساخت query برای insert
                insert_columns = ', '.join(quote_identifier(col) for col in row_dict.keys())
                placeholders = ', '.join(['?' for _ in row_dict])
                values = tuple(row_dict.values())
                
                query = f"INSERT OR REPLACE INTO {quote_identifier(table_name)} ({insert_columns}) VALUES ({placeholders})"
                cursor_cafe.execute(query, values)
                migrated_count += 1
                
            except Exception as e:
                print(f"    ✗ خطا در انتقال رکورد از {table_name}: {e}")
                continue
        
        cafe_conn.commit()
        print(f"  ✓ {table_name}: {migrated_count} رکورد منتقل شد")
        return migrated_count, id_mapping
        
    except Exception as e:
        print(f"  ✗ خطا در انتقال {table_name}: {e}")
        return 0, id_mapping

def update_foreign_keys(cafe_conn, id_mappings):
    """به‌روزرسانی foreign key ها بعد از تغییر ID ها"""
    print("\n=== به‌روزرسانی Foreign Key ها ===")
    cursor = cafe_conn.cursor()
    
    # به‌روزرسانی order.customer_id
    if 'customer' in id_mappings:
        for old_id, new_id in id_mappings['customer'].items():
            cursor.execute(f"UPDATE {quote_identifier('order')} SET customer_id = ? WHERE customer_id = ?", (new_id, old_id))
    
    # به‌روزرسانی order.user_id
    if 'user' in id_mappings:
        for old_id, new_id in id_mappings['user'].items():
            cursor.execute(f"UPDATE {quote_identifier('order')} SET user_id = ? WHERE user_id = ?", (new_id, old_id))
    
    # به‌روزرسانی order.table_id
    if 'table' in id_mappings:
        for old_id, new_id in id_mappings['table'].items():
            cursor.execute(f"UPDATE {quote_identifier('order')} SET table_id = ? WHERE table_id = ?", (new_id, old_id))
    
    # به‌روزرسانی order_item.order_id
    if 'order' in id_mappings:
        for old_id, new_id in id_mappings['order'].items():
            cursor.execute(f"UPDATE {quote_identifier('order_item')} SET order_id = ? WHERE order_id = ?", (new_id, old_id))
    
    # به‌روزرسانی order_item.menu_item_id
    if 'menu_item' in id_mappings:
        for old_id, new_id in id_mappings['menu_item'].items():
            cursor.execute(f"UPDATE {quote_identifier('order_item')} SET menu_item_id = ? WHERE menu_item_id = ?", (new_id, old_id))
    
    # به‌روزرسانی menu_item.category_id
    if 'category' in id_mappings:
        for old_id, new_id in id_mappings['category'].items():
            cursor.execute(f"UPDATE {quote_identifier('menu_item')} SET category_id = ? WHERE category_id = ?", (new_id, old_id))
    
    # به‌روزرسانی table_item.table_id
    if 'table' in id_mappings:
        for old_id, new_id in id_mappings['table'].items():
            cursor.execute(f"UPDATE {quote_identifier('table_item')} SET table_id = ? WHERE table_id = ?", (new_id, old_id))
    
    # به‌روزرسانی table_item.menu_item_id
    if 'menu_item' in id_mappings:
        for old_id, new_id in id_mappings['menu_item'].items():
            cursor.execute(f"UPDATE {quote_identifier('table_item')} SET menu_item_id = ? WHERE menu_item_id = ?", (new_id, old_id))
    
    # به‌روزرسانی menu_item_material.menu_item_id
    if 'menu_item' in id_mappings:
        for old_id, new_id in id_mappings['menu_item'].items():
            cursor.execute(f"UPDATE {quote_identifier('menu_item_material')} SET menu_item_id = ? WHERE menu_item_id = ?", (new_id, old_id))
    
    # به‌روزرسانی menu_item_material.raw_material_id
    if 'raw_material' in id_mappings:
        for old_id, new_id in id_mappings['raw_material'].items():
            cursor.execute(f"UPDATE {quote_identifier('menu_item_material')} SET raw_material_id = ? WHERE raw_material_id = ?", (new_id, old_id))
    
    # به‌روزرسانی material_purchase.raw_material_id
    if 'raw_material' in id_mappings:
        for old_id, new_id in id_mappings['raw_material'].items():
            cursor.execute(f"UPDATE {quote_identifier('material_purchase')} SET raw_material_id = ? WHERE raw_material_id = ?", (new_id, old_id))
    
    # به‌روزرسانی action_log.user_id
    if 'user' in id_mappings:
        for old_id, new_id in id_mappings['user'].items():
            cursor.execute(f"UPDATE {quote_identifier('action_log')} SET user_id = ? WHERE user_id = ?", (new_id, old_id))
    
    cafe_conn.commit()
    print("✓ Foreign Key ها به‌روزرسانی شدند\n")

def main():
    """تابع اصلی مهاجرت"""
    print("=" * 60)
    print("اسکریپت مهاجرت دیتابیس‌ها")
    print("=" * 60)
    
    # بررسی وجود فایل‌های دیتابیس
    if not os.path.exists(CAFE_DB):
        print(f"✗ خطا: دیتابیس {CAFE_DB} پیدا نشد!")
        return
    
    # اگر cafe1.db وجود نداشت، از backup استفاده می‌کنیم
    cafe1_db_path = CAFE1_DB
    cafe1_backup = CAFE1_DB + '.backup'
    if not os.path.exists(CAFE1_DB):
        if os.path.exists(cafe1_backup):
            print(f"⚠ دیتابیس {CAFE1_DB} پیدا نشد، از پشتیبان استفاده می‌شود: {cafe1_backup}")
            cafe1_db_path = cafe1_backup
        else:
            print(f"✗ خطا: دیتابیس {CAFE1_DB} و پشتیبان آن پیدا نشد!")
            return
    
    # ایجاد backup
    print("\n=== ایجاد پشتیبان ===")
    backup_cafe = CAFE_DB + '.backup'
    backup_cafe1 = cafe1_db_path + '.backup2'  # نام متفاوت برای backup از backup
    
    try:
        shutil.copy2(CAFE_DB, backup_cafe)
        print(f"✓ پشتیبان cafe.db ایجاد شد: {backup_cafe}")
        if cafe1_db_path != cafe1_backup:  # فقط اگر فایل اصلی بود، backup بگیر
            shutil.copy2(cafe1_db_path, backup_cafe1)
            print(f"✓ پشتیبان cafe1.db ایجاد شد: {backup_cafe1}")
    except Exception as e:
        print(f"✗ خطا در ایجاد پشتیبان: {e}")
        return
    
    # اتصال به دیتابیس‌ها
    try:
        cafe_conn = sqlite3.connect(CAFE_DB)
        cafe1_conn = sqlite3.connect(cafe1_db_path)
        print("\n✓ اتصال به دیتابیس‌ها برقرار شد")
    except Exception as e:
        print(f"✗ خطا در اتصال به دیتابیس‌ها: {e}")
        return
    
    try:
        # مرحله 1: حذف داده‌های بعد از فروردین از cafe
        delete_data_after_march(cafe_conn)
        
        # مرحله 2: انتقال داده‌ها از cafe1 به cafe
        print("\n=== انتقال داده‌ها از cafe1 به cafe ===")
        
        # ترتیب انتقال: ابتدا جداول مستقل، سپس جداول وابسته
        independent_tables = ['category', 'user', 'settings', 'raw_material']
        dependent_tables = ['menu_item', 'customer', 'table', 'material_purchase']
        order_tables = ['order']
        order_item_tables = ['order_item', 'table_item', 'menu_item_material', 'action_log']
        
        all_tables = independent_tables + dependent_tables + order_tables + order_item_tables
        
        # محاسبه offset برای ID ها
        max_ids = {}
        for table in all_tables:
            max_ids[table] = get_max_id(cafe_conn, table)
        
        # استفاده از بیشترین ID به عنوان offset پایه
        base_offset = max(max_ids.values()) if max_ids.values() else 10000
        
        total_migrated = 0
        all_id_mappings = {}  # {table_name: {old_id: new_id}}
        
        # انتقال جداول مستقل
        for table in independent_tables:
            count, id_mapping = migrate_table(cafe_conn, cafe1_conn, table, base_offset, all_id_mappings)
            total_migrated += count
            if id_mapping:
                all_id_mappings[table] = id_mapping
        
        # انتقال جداول وابسته
        for table in dependent_tables:
            count, id_mapping = migrate_table(cafe_conn, cafe1_conn, table, base_offset, all_id_mappings)
            total_migrated += count
            if id_mapping:
                all_id_mappings[table] = id_mapping
        
        # انتقال سفارش‌ها
        for table in order_tables:
            count, id_mapping = migrate_table(cafe_conn, cafe1_conn, table, base_offset, all_id_mappings)
            total_migrated += count
            if id_mapping:
                all_id_mappings[table] = id_mapping
        
        # انتقال آیتم‌های سفارش (نیاز به به‌روزرسانی foreign key دارند)
        for table in order_item_tables:
            count, id_mapping = migrate_table(cafe_conn, cafe1_conn, table, base_offset, all_id_mappings)
            total_migrated += count
            if id_mapping:
                all_id_mappings[table] = id_mapping
        
        print(f"\n✓ مجموع {total_migrated} رکورد منتقل شد")
        
        # مرحله 2.5: به‌روزرسانی foreign key ها
        update_foreign_keys(cafe_conn, all_id_mappings)
        
        # مرحله 3: حذف دیتابیس cafe1 (فقط اگر فایل اصلی بود)
        print("\n=== حذف دیتابیس cafe1 ===")
        cafe1_conn.close()
        cafe_conn.close()
        
        # فقط اگر از فایل اصلی استفاده کردیم، آن را حذف می‌کنیم
        if cafe1_db_path == CAFE1_DB and os.path.exists(CAFE1_DB):
            try:
                os.remove(CAFE1_DB)
                print(f"✓ دیتابیس {CAFE1_DB} حذف شد")
            except Exception as e:
                print(f"✗ خطا در حذف دیتابیس cafe1: {e}")
                print("  می‌توانید به صورت دستی آن را حذف کنید")
        else:
            print(f"⚠ فایل اصلی {CAFE1_DB} وجود نداشت، از backup استفاده شد")
        
        print("\n" + "=" * 60)
        print("✓ مهاجرت با موفقیت انجام شد!")
        print("=" * 60)
        print(f"\nپشتیبان‌ها در این مسیرها ذخیره شده‌اند:")
        print(f"  - {backup_cafe}")
        if os.path.exists(backup_cafe1):
            print(f"  - {backup_cafe1}")
        print("\nدر صورت نیاز می‌توانید از پشتیبان‌ها استفاده کنید.")
        
    except Exception as e:
        print(f"\n✗ خطا در فرآیند مهاجرت: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠ در صورت بروز مشکل، می‌توانید از پشتیبان‌ها استفاده کنید.")

if __name__ == '__main__':
    main()

