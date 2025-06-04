from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.models import db, Category, MenuItem
from flask_login import login_required

menu_bp = Blueprint('menu', __name__)

@menu_bp.route('/menu')
@login_required
def show_menu():
    # دریافت همه دسته‌بندی‌ها به ترتیب فیلد order
    # Note: This route loads all categories and their items for the menu management page
    categories = Category.query.order_by(Category.order).all()
    
    # دریافت همه آیتم‌های منو و گروه‌بندی آنها بر اساس دسته‌بندی
    # This grouping logic might be redundant if using category.menu_items relationship
    # menu_items = MenuItem.query.all()
    # menu_by_category = {}
    # for category in categories:
    #     menu_by_category[category.id] = {
    #         'name': category.name,
    #         'items': []
    #     }
    # for item in menu_items:
    #     if item.category_id in menu_by_category:
    #         menu_by_category[item.category_id]['items'].append(item)
    
    # Passing categories directly with loaded menu_items relationship is usually sufficient
    return render_template('menu/menu.html', categories=categories) # Removed menu_by_category as it's redundant with relationship

@menu_bp.route('/categories')
@login_required
def categories_list():
    categories = Category.query.order_by(Category.order).all()
    return render_template('menu/categories.html', categories=categories)

# Note: The following add/edit routes seem to be form-based, not JSON API based.
# The JSON API routes like /save, /category/save, etc., are handled separately below.

@menu_bp.route('/category/add', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'POST':
        name = request.form.get('name')
        order = request.form.get('order', 0)
        
        if not name:
            flash('نام دسته‌بندی الزامی است.', 'danger')
            return redirect(url_for('menu.add_category'))
        
        category = Category(name=name, order=order)
        db.session.add(category)
        db.session.commit()
        
        flash('دسته‌بندی جدید با موفقیت اضافه شد.', 'success')
        return redirect(url_for('menu.categories_list'))
    
    return render_template('menu/add_category.html')

@menu_bp.route('/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        order = request.form.get('order', category.order)
        
        if not name:
            flash('نام دسته‌بندی الزامی است.', 'danger')
            return redirect(url_for('menu.edit_category', id=id))
        
        category.name = name
        category.order = order
        db.session.commit()
        
        flash('دسته‌بندی با موفقیت به‌روزرسانی شد.', 'success')
        return redirect(url_for('menu.categories_list'))
    
    return render_template('menu/edit_category.html', category=category)

# This route seems redundant with delete_category_json below, keeping for now based on context
@menu_bp.route('/category/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category_api(category_id):
    category = Category.query.get_or_404(category_id)
    if category.menu_items:
        return jsonify({'status': 'error', 'message': 'ابتدا آیتم‌های این دسته را حذف کنید.'})
    db.session.delete(category)
    db.session.commit()
    return jsonify({'status': 'deleted'})

@menu_bp.route('/menu/item/add', methods=['GET', 'POST'])
@login_required
def add_menu_item():
    categories = Category.query.order_by(Category.order).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        stock = request.form.get('stock', 0)
        category_id = request.form.get('category_id')
        
        if not name or not price or not category_id:
            flash('تمام فیلدهای ضروری را پر کنید.', 'danger')
            return redirect(url_for('menu.add_menu_item'))
        
        try:
            price = int(price)
            stock = int(stock)
        except ValueError:
            flash('قیمت و موجودی باید عدد باشند.', 'danger')
            return redirect(url_for('menu.add_menu_item'))
        
        menu_item = MenuItem(name=name, price=price, stock=stock, category_id=category_id)
        db.session.add(menu_item)
        db.session.commit()
        
        flash('آیتم منو با موفقیت اضافه شد.', 'success')
        return redirect(url_for('menu.show_menu'))
    
    return render_template('menu/add_menu_item.html', categories=categories) # Fixed variable name

@menu_bp.route('/menu/item/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_menu_item(id):
    menu_item = MenuItem.query.get_or_404(id)
    categories = Category.query.order_by(Category.order).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        stock = request.form.get('stock', menu_item.stock)
        category_id = request.form.get('category_id')
        
        if not name or not price or not category_id:
            flash('تمام فیلدهای ضروری را پر کنید.', 'danger')
            return redirect(url_for('menu.edit_menu_item', id=id))
        
        try:
            price = int(price)
            stock = int(stock)
        except ValueError:
            flash('قیمت و موجودی باید عدد باشند.', 'danger')
            return redirect(url_for('menu.edit_menu_item', id=id))
        
        menu_item.name = name
        menu_item.price = price
        menu_item.stock = stock
        menu_item.category_id = category_id
        db.session.commit()
        
        flash('آیتم منو با موفقیت به‌روزرسانی شد.', 'success')
        return redirect(url_for('menu.show_menu'))
    
    return render_template('menu/edit_menu_item.html', menu_item=menu_item, categories=categories)

# Modified the delete route to match the requested signature and logic
# Adjusted route to avoid double '/menu' prefix when blueprint registered
# Now the endpoint matches the JavaScript call to '/menu/item/delete/<id>'
@menu_bp.route('/item/delete/<int:item_id>', methods=['POST'])
@login_required

def delete_menu_item(item_id):
    item = MenuItem.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'آیتم یافت نشد'}), 404
        
    # Prevent deletion if the item has related order items
    if item.order_items:
        return (
            jsonify({'success': False, 'message': 'آیتم در سفارش‌ها استفاده شده و قابل حذف نیست'}),
            400,
        )

    # If the item exists in previous orders, only deactivate it
    # to maintain database integrity without breaking historical data
    if item.order_items:
        item.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'آیتم غیرفعال شد'})

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[!] خطا هنگام حذف آیتم: {e}")  # لاگ در ترمینال
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطای داخلی سرور'}), 500



@menu_bp.route('/save', methods=['POST'])
@login_required # Added login_required
def save_menu_item_json():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400 # Changed to jsonify
    
    item_id = data.get('id')
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock') or 0
    category_id = data.get('category_id')
    
    if not name or price is None or not category_id: # Check price is not None
        return jsonify({'status': 'error', 'message': 'نام، قیمت و دسته‌بندی الزامی هستند'}), 400
    
    try:
        price = int(price)
        stock = int(stock)
        category_id = int(category_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'مقدار عددی نامعتبر یا دسته‌بندی نامعتبر است'}), 400
    
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'status': 'error', 'message': 'دسته‌بندی انتخاب شده وجود ندارد'}), 400
    
    if item_id:
        item = MenuItem.query.get(item_id)
        if not item:
            return jsonify({'status': 'error', 'message': 'آیتم یافت نشد'}), 404
        item.name = name
        item.price = price
        item.stock = stock
        item.category_id = category_id
    else:
        item = MenuItem(name=name, price=price, stock=stock, category_id=category_id)
        db.session.add(item)
    
    db.session.commit()
    return jsonify({'status': 'success'}) # Changed to jsonify

@menu_bp.route('/category/save', methods=['POST'])
@login_required # Added login_required
def save_category_json():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    name = data.get('name')
    description = data.get('description')
    # Assuming 'order' is not part of the category modal form based on menu.html context
    # If it is, you'd need to add it to the form and here.
    # For now, let's assume order is handled elsewhere or defaults.
    # order = int(data.get('order') or 0) # Removed as it's not in the modal form
    
    if not name:
        return jsonify({'status': 'error', 'message': 'نام الزامی است'}), 400
    
    # Check if category with the same name already exists (optional but good practice)
    existing_category = Category.query.filter_by(name=name).first()
    if existing_category:
         return jsonify({'status': 'error', 'message': 'دسته‌بندی با این نام از قبل وجود دارد'}), 400

    # Determine the next order value (simple approach: max order + 1)
    max_order_category = Category.query.order_by(Category.order.desc()).first()
    next_order = (max_order_category.order + 1) if max_order_category else 0

    category = Category(name=name, description=description, order=next_order) # Use calculated order
    db.session.add(category)
    db.session.commit()
    
    return jsonify({'status': 'success'})

# This route seems redundant with update_category_json below, keeping for now based on context
@menu_bp.route('/category/update/<int:id>', methods=['POST'])
@login_required # Added login_required
def update_category(id):
    data = request.get_json()
    name = data.get('name')
    order = data.get('order')
    category = Category.query.get_or_404(id)
    
    if not name or order is None: # Check for name and order
         return jsonify({'status': 'error', 'message': 'نام و ترتیب الزامی هستند'}), 400
         
    try:
        order = int(order)
    except ValueError:
         return jsonify({'status': 'error', 'message': 'ترتیب باید عدد باشد'}), 400

    category.name = name
    category.order = order
    db.session.commit()
    return jsonify({'status': 'success'})

# This route seems redundant with delete_category_api above, keeping for now based on context
@menu_bp.route('/category/delete/<int:id>', methods=['POST'])
@login_required # Added login_required
def delete_category_json(id):
    category = Category.query.get_or_404(id)
    # Optional: Check if category has items before deleting
    if category.menu_items:
         return jsonify({'status': 'error', 'message': 'ابتدا آیتم‌های این دسته را حذف کنید.'}), 400
    db.session.delete(category)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'دسته‌بندی با موفقیت حذف شد'}) # Added success message

# مسیر جدید برای فعال/غیرفعال‌سازی دسته‌بندی
@menu_bp.route('/category/toggle/<int:id>', methods=['POST'])
@login_required # Added login_required
def toggle_category(id):
    category = Category.query.get_or_404(id)
    category.is_active = not category.is_active
    db.session.commit()
    return jsonify({'status': 'success', 'active': category.is_active})

@menu_bp.route('/menu/stocks')
@login_required
def get_menu_stocks():
    items = MenuItem.query.all()
    data = [{'id': item.id, 'stock': item.stock} for item in items]
    return jsonify(success=True, stocks=data)

# --- START: مسیر جدید برای دریافت آیتم‌های منو برای داشبورد (ساختار قبلی) ---
# Keeping this route as it was added previously, although /menu-data is requested now
@menu_bp.route('/menu/dashboard')
@login_required
def dashboard_menu_items():
    items = MenuItem.query.all() # یا می‌توانید فیلتر کنید مثلاً فقط آیتم‌های فعال
    result = []
    for item in items:
        result.append({
            'id': item.id,
            'name': item.name,
            'price': item.price,
            'stock': item.stock
            # 'category_name': item.category.name if item.category else 'بدون دسته‌بندی' # اگر نیاز به نام دسته‌بندی هم دارید
        })
    return jsonify({'success': True, 'items': result})
# --- END: مسیر جدید برای دریافت آیتم‌های منو برای داشبورد (ساختار قبلی) ---


# --- START: مسیر جدید برای دریافت داده‌ی منو با ساختار دسته‌بندی شده (طبق درخواست) ---
@menu_bp.route('/menu-data')
@login_required
def get_menu_data():
    # دریافت دسته‌بندی‌های فعال به ترتیب فیلد order
    categories = Category.query.filter_by(is_active=True).order_by(Category.order).all()
    data = []
    for category in categories:
        # دریافت آیتم‌های فعال هر دسته‌بندی
        items = [{
            'id': item.id,
            'name': item.name,
            'price': item.price,
            'stock': item.stock
        } for item in category.menu_items if item.is_active] # فرض بر اینکه MenuItem هم فیلد is_active دارد
        
        # اضافه کردن دسته‌بندی به لیست نتیجه
        # اگر می‌خواهید دسته‌بندی‌های بدون آیتم فعال نمایش داده نشوند، شرط if items: را اضافه کنید
        data.append({
            'id': category.id,
            'name': category.name,
            'items': items
        })
            
    return jsonify(data)
# --- END: مسیر جدید ---
