from flask import Flask, render_template
from config import Config
from models.models import db, Category, MenuItem
from utils.helpers import register_jinja_filters
from datetime import datetime
from flask_migrate import Migrate



from flask_login import LoginManager, current_user

def seed_data():
    # اگر قبلاً داده‌ای اضافه نشده، فقط یک بار اجرا شود
    if not Category.query.first():
        # تعریف دسته‌بندی‌ها با ترتیب مشخص
        categories = [
            {'name': 'Hot Espresso', 'order': 1},
            {'name': 'Ice Cream', 'order': 2},
            {'name': 'Cold Espresso', 'order': 3},
            {'name': 'Hot Drinks', 'order': 4},
            {'name': 'Tea (Hot/Cold)', 'order': 5},
            {'name': 'Macha', 'order': 6},
            {'name': 'Juice & Smoothie', 'order': 7},
            {'name': 'Shake', 'order': 8},
            {'name': 'Beer', 'order': 9}
        ]
        
        # اضافه کردن دسته‌بندی‌ها به دیتابیس
        for cat_data in categories:
            category = Category(name=cat_data['name'], order=cat_data['order'])
            db.session.add(category)
        
        db.session.commit()
        print('✅ دسته‌بندی‌های منو با موفقیت اضافه شدند.')
        
        # اضافه کردن چند آیتم منو به عنوان نمونه
        sample_items = [
            {'name': 'اسپرسو', 'price': 45000, 'category_name': 'Hot Espresso', 'stock': 100},
            {'name': 'کاپوچینو', 'price': 65000, 'category_name': 'Hot Espresso', 'stock': 100},
            {'name': 'لاته', 'price': 70000, 'category_name': 'Hot Espresso', 'stock': 100},
            {'name': 'آیس کافی', 'price': 75000, 'category_name': 'Cold Espresso', 'stock': 50},
            {'name': 'آیس لاته', 'price': 80000, 'category_name': 'Cold Espresso', 'stock': 50},
            {'name': 'چای سبز', 'price': 40000, 'category_name': 'Tea (Hot/Cold)', 'stock': 200},
            {'name': 'چای ترش', 'price': 45000, 'category_name': 'Tea (Hot/Cold)', 'stock': 200},
            {'name': 'آب پرتقال', 'price': 60000, 'category_name': 'Juice & Smoothie', 'stock': 30},
            {'name': 'شیک شکلات', 'price': 85000, 'category_name': 'Shake', 'stock': 40},
            {'name': 'بستنی وانیل', 'price': 50000, 'category_name': 'Ice Cream', 'stock': 60}
        ]
        
        # اضافه کردن آیتم‌های منو به دیتابیس
        for item_data in sample_items:
            category = Category.query.filter_by(name=item_data['category_name']).first()
            if category:
                item = MenuItem(
                    name=item_data['name'],
                    price=item_data['price'],
                    stock=item_data['stock'],
                    category_id=category.id
                )
                db.session.add(item)
        
        db.session.commit()
        print('✅ آیتم‌های نمونه منو با موفقیت اضافه شدند.')

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    migrate = Migrate(app, db)


    # --- اضافه کردن LoginManager ---
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    # -------------------------------

    # --- اضافه کردن user_loader ---
    from models.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    # -------------------------------

    # ثبت فیلترهای Jinja2 برای قالب‌ها
    register_jinja_filters(app)

    # Blueprint imports
    from routes.menu import menu_bp
    from routes.order import order_bp
    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp

    app.register_blueprint(menu_bp, url_prefix='/menu')
    app.register_blueprint(order_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    # context processor برای ارسال now به همه قالب‌ها
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow}

    # صفحه اصلی
    from flask import redirect, url_for

    @app.route('/')
    def index():

        if current_user.is_authenticated:
            # اگر کاربر لاگین کرده، به داشبورد هدایت کن
            return redirect(url_for('dashboard.dashboard'))
        else:
            # اگر لاگین نکرده، به صفحه لاگین هدایت کن
            return redirect(url_for('auth.login'))

    # هندلر خطای 404
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    # هندلر خطای 500
    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_data()  # فقط یک بار اجرا شود

        # --- افزودن کاربران تستی ---
        from werkzeug.security import generate_password_hash
        from models.models import User

        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password_hash=generate_password_hash('123456789'), role='admin')
            user1 = User(username='user1', password_hash=generate_password_hash('123'), role='waiter')
            user2 = User(username='user2', password_hash=generate_password_hash('123'), role='waiter')
            db.session.add_all([admin, user1, user2])
            db.session.commit()
            print('✅ سه کاربر جدید اضافه شدند.')
        else:
            print('ℹ کاربران قبلاً اضافه شده‌اند.')
    app.run(debug=True)
