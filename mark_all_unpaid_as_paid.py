"""
اسکریپت برای تغییر وضعیت تمام سفارش‌های پرداخت نشده به پرداخت شده
این اسکریپت را یک بار اجرا کنید تا تمام سفارش‌های پرداخت نشده به پرداخت شده تغییر یابند.
"""

from app import create_app
from models.models import db, Order
from datetime import datetime
import pytz

def mark_all_unpaid_as_paid():
    """تغییر وضعیت تمام سفارش‌های پرداخت نشده به پرداخت شده"""
    app = create_app()
    
    with app.app_context():
        iran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(iran_tz)
        
        # پیدا کردن تمام سفارش‌های پرداخت نشده
        unpaid_orders = Order.query.filter(Order.status == 'پرداخت نشده').all()
        
        if not unpaid_orders:
            print("✅ هیچ سفارش پرداخت نشده‌ای یافت نشد.")
            return
        
        count = 0
        total_amount = 0
        
        print(f"📋 پیدا شد: {len(unpaid_orders)} سفارش پرداخت نشده")
        print("🔄 در حال تغییر وضعیت...")
        
        for order in unpaid_orders:
            order.status = 'پرداخت شده'
            if not order.paid_at:
                order.paid_at = now
            if not order.payment_method:
                order.payment_method = 'کارتخوان'  # پیش‌فرض کارتخوان
            count += 1
            total_amount += order.final_amount
        
        try:
            db.session.commit()
            print(f"✅ موفق! {count} سفارش با مجموع {total_amount:,} به وضعیت 'پرداخت شده' تغییر یافت.")
            print(f"📊 مجموع مبلغ: {total_amount:,}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطا در ذخیره تغییرات: {str(e)}")
            raise

if __name__ == '__main__':
    print("=" * 50)
    print("  تغییر وضعیت سفارش‌های پرداخت نشده")
    print("=" * 50)
    print()
    
    response = input("⚠️  آیا مطمئن هستید که می‌خواهید تمام سفارش‌های پرداخت نشده را به 'پرداخت شده' تغییر دهید؟ (بله/خیر): ")
    
    if response.lower() in ['بله', 'yes', 'y', 'ب']:
        try:
            mark_all_unpaid_as_paid()
            print()
            print("✅ عملیات با موفقیت انجام شد!")
        except Exception as e:
            print()
            print(f"❌ خطا: {str(e)}")
    else:
        print("❌ عملیات لغو شد.")

