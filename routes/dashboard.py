from flask import Blueprint, render_template
from models.models import Order, Category, MenuItem, Customer
from flask_login import login_required

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def dashboard():
    # Get all categories with their menu items
    categories = Category.query.filter_by(is_active=True).order_by(Category.order).all()
    
    # Get all customers for the datalist
    customers = Customer.query.all()
    
    return render_template('dashboard.html', 
                          orders=Order.query.all(),
                          categories=categories, 
                          customers=customers)