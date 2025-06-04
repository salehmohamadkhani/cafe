# توابع مربوط به چاپ فاکتور و پرینتر اینجا قرار می‌گیرند.

def print_invoice(order):
    """Simulate printing an invoice for the given order."""
    print(f"--- فاکتور سفارش شماره {order.id} ---")
    for item in order.order_items:
        print(f"{item.quantity} x {item.menu_item_id} @ {item.price} تومان")
    print(f"جمع کل: {order.total_price} تومان (شامل مالیات {order.tax_percent}%)")