# -*- coding: utf-8 -*-
from app import create_app
from models.models import db, Order
from datetime import datetime
import pytz

app = create_app()
with app.app_context():
    iran_tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(iran_tz)
    
    unpaid_orders = Order.query.filter(Order.status == 'پرداخت نشده').all()
    
    if not unpaid_orders:
        print("No unpaid orders found.")
    else:
        count = 0
        total = 0
        for order in unpaid_orders:
            order.status = 'پرداخت شده'
            if not order.paid_at:
                order.paid_at = now
            if not order.payment_method:
                order.payment_method = 'کارتخوان'
            count += 1
            total += order.final_amount
        
        db.session.commit()
        print(f"Updated {count} orders. Total: {total:,} Toman")

