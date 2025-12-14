# cafe1/routes/pos.py
from flask import Blueprint, render_template
from models.models import MenuItem  # در cafe1 همینجاست

bp = Blueprint("pos", __name__, url_prefix="/pos")

@bp.get("/new")
def new_order():
    """
    صفحه‌ی سفارش جدید: فقط دیتای منو را لود می‌کنیم و می‌فرستیم به تمپلیت.
    تمپلیت را در مرحله‌ی بعد می‌سازیم.
    """
    # بعضی دیتابیس‌ها ممکنه name نداشته باشن و به‌جاش title داشته باشن.
    try:
        items = MenuItem.query.order_by(MenuItem.name).all()
    except Exception:
        items = MenuItem.query.order_by(getattr(MenuItem, "title")).all()
    return render_template("pos/pos.html", items=items)
