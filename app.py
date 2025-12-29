import sys
import io

# تنظیم encoding برای stdout و stderr برای پشتیبانی از فارسی و یونیکد
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager
from sqlalchemy import inspect, text
from config import Config
from models.models import db, User, Settings, backfill_invoice_identifiers, assign_random_birth_dates_to_old_customers
from models.master_models import MasterUser, CafeTenant  # noqa: F401 (register master tables)
from utils.helpers import register_jinja_filters

# Import blueprints
from routes.auth import auth_bp
from routes.master_portal import master_bp
from routes.tenant_auth import tenant_auth_bp
from routes.tenant import tenant_bp
from routes.tenant_dashboard import tenant_dashboard_bp
from routes.menu import menu_bp
from routes.order import order_bp
from routes.dashboard import dashboard_bp
from routes.admin import admin_bp
from routes.pos import bp as pos_bp
from routes.table import table_bp
from routes.takeaway import takeaway_bp

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'لطفاً برای دسترسی به این صفحه وارد شوید.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Apply lightweight schema migrations (e.g., missing columns on SQLite)
    with app.app_context():
        engine = db.get_engine()
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        if 'customer' in existing_tables:
            customer_columns = {col['name'] for col in inspector.get_columns('customer')}
            if 'birth_date' not in customer_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE customer ADD COLUMN birth_date DATE'))
        if 'table' in existing_tables:
            table_columns = {col['name'] for col in inspector.get_columns('table')}
            if 'is_reserved' not in table_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE "table" ADD COLUMN is_reserved BOOLEAN DEFAULT 0'))
        if 'menu_item_material' in existing_tables:
            material_columns = {col['name'] for col in inspector.get_columns('menu_item_material')}
            if 'raw_material_id' not in material_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE "menu_item_material" ADD COLUMN raw_material_id INTEGER REFERENCES raw_material(id)'))
        # Create warehouse_material_min_stock table if it doesn't exist
        if 'warehouse_material_min_stock' not in existing_tables:
            with engine.begin() as conn:
                conn.execute(text('''
                    CREATE TABLE warehouse_material_min_stock (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        raw_material_id INTEGER NOT NULL,
                        warehouse_id INTEGER NOT NULL,
                        min_stock REAL NOT NULL DEFAULT 0.0,
                        created_at DATETIME,
                        updated_at DATETIME,
                        FOREIGN KEY (raw_material_id) REFERENCES raw_material(id),
                        FOREIGN KEY (warehouse_id) REFERENCES warehouse(id),
                        UNIQUE(raw_material_id, warehouse_id)
                    )
                '''))
        # Migrate pre_production_stock table to add warehouse_id
        if 'pre_production_stock' in existing_tables:
            pre_production_stock_columns = {col['name'] for col in inspector.get_columns('pre_production_stock')}
            if 'warehouse_id' not in pre_production_stock_columns:
                # Get pre_production warehouse ID
                with engine.begin() as conn:
                    # First, add the warehouse_id column (nullable initially)
                    conn.execute(text('ALTER TABLE pre_production_stock ADD COLUMN warehouse_id INTEGER'))
                    # Get pre_production warehouse ID
                    result = conn.execute(text('SELECT id FROM warehouse WHERE code = :code'), {'code': 'pre_production'})
                    pre_prod_wh_row = result.fetchone()
                    if pre_prod_wh_row:
                        pre_prod_wh_id = pre_prod_wh_row[0]
                        # Update all existing records to point to pre_production warehouse
                        conn.execute(text('UPDATE pre_production_stock SET warehouse_id = :wh_id WHERE warehouse_id IS NULL'), {'wh_id': pre_prod_wh_id})
                    # Make warehouse_id NOT NULL and add foreign key
                    # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
                    conn.execute(text('''
                        CREATE TABLE pre_production_stock_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            pre_production_item_id INTEGER NOT NULL,
                            warehouse_id INTEGER NOT NULL,
                            quantity REAL NOT NULL DEFAULT 0.0,
                            unit VARCHAR(32) NOT NULL DEFAULT 'عدد',
                            created_at DATETIME,
                            updated_at DATETIME,
                            FOREIGN KEY (pre_production_item_id) REFERENCES pre_production_item(id),
                            FOREIGN KEY (warehouse_id) REFERENCES warehouse(id),
                            UNIQUE(pre_production_item_id, warehouse_id)
                        )
                    '''))
                    # Copy data
                    conn.execute(text('''
                        INSERT INTO pre_production_stock_new 
                        (id, pre_production_item_id, warehouse_id, quantity, unit, created_at, updated_at)
                        SELECT id, pre_production_item_id, warehouse_id, quantity, unit, created_at, updated_at
                        FROM pre_production_stock
                    '''))
                    # Drop old table and rename new one
                    conn.execute(text('DROP TABLE pre_production_stock'))
                    conn.execute(text('ALTER TABLE pre_production_stock_new RENAME TO pre_production_stock'))
        if 'order' in existing_tables:
            order_columns = {col['name'] for col in inspector.get_columns('order')}
            if 'daily_sequence' not in order_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE "order" ADD COLUMN daily_sequence INTEGER'))
            if 'invoice_uid' not in order_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE "order" ADD COLUMN invoice_uid VARCHAR(64)'))
        if 'order_item' in existing_tables:
            order_item_columns = {col['name'] for col in inspector.get_columns('order_item')}
            if 'is_deleted' not in order_item_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE order_item ADD COLUMN is_deleted BOOLEAN DEFAULT 0'))
            if 'removal_reason' not in order_item_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE order_item ADD COLUMN removal_reason VARCHAR(256)'))
        db.create_all()
        inspector = inspect(engine)
        if 'menu_item_material' in inspector.get_table_names():
            material_columns = {col['name'] for col in inspector.get_columns('menu_item_material')}
            if 'unit' not in material_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE "menu_item_material" ADD COLUMN unit VARCHAR(32) DEFAULT \'عدد\''))
            if 'pre_production_item_id' not in material_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE "menu_item_material" ADD COLUMN pre_production_item_id INTEGER REFERENCES pre_production_item(id)'))
        if 'raw_material' in inspector.get_table_names():
            raw_material_columns = {col['name'] for col in inspector.get_columns('raw_material')}
            if 'min_stock' not in raw_material_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE "raw_material" ADD COLUMN min_stock REAL'))
        if 'table' in inspector.get_table_names():
            table_columns = {col['name'] for col in inspector.get_columns('table')}
            if 'area_id' not in table_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE "table" ADD COLUMN area_id INTEGER REFERENCES table_area(id)'))
        if 'settings' in inspector.get_table_names():
            settings_columns = {col['name'] for col in inspector.get_columns('settings')}
            if 'service_charge' not in settings_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE settings ADD COLUMN service_charge FLOAT DEFAULT 0'))
            if 'currency' not in settings_columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE settings ADD COLUMN currency VARCHAR(16) DEFAULT ''"))
            if 'card_number' not in settings_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE settings ADD COLUMN card_number VARCHAR(64)'))
            if 'instagram' not in settings_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE settings ADD COLUMN instagram VARCHAR(256)'))
            if 'telegram' not in settings_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE settings ADD COLUMN telegram VARCHAR(256)'))
            if 'website' not in settings_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE settings ADD COLUMN website VARCHAR(256)'))

        # Lightweight migration for cost_formula_settings.personnel column (JSON stored as TEXT)
        if 'cost_formula_settings' in inspector.get_table_names():
            cfs_columns = {col['name'] for col in inspector.get_columns('cost_formula_settings')}
            if 'personnel' not in cfs_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE cost_formula_settings ADD COLUMN personnel TEXT'))
            if 'cost_control_percent' not in cfs_columns:
                with engine.begin() as conn:
                    conn.execute(text('ALTER TABLE cost_formula_settings ADD COLUMN cost_control_percent INTEGER DEFAULT 0'))

        backfill_invoice_identifiers()
        
        # اختصاص تاریخ تولد تصادفی به مشتریان قدیمی
        assign_random_birth_dates_to_old_customers()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(master_bp)
    app.register_blueprint(tenant_auth_bp)
    app.register_blueprint(tenant_bp)
    app.register_blueprint(tenant_dashboard_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(table_bp)
    app.register_blueprint(takeaway_bp)

    # Convenient alias to master login (main entrypoint for multi-cafe)
    @app.route('/login')
    def master_login_alias():
        return redirect(url_for('master.login'))
    
    # Register index route
    @app.route('/')
    def index():
        return render_template('index.html')

    # Make business settings (e.g., cafe name) available in all templates
    @app.context_processor
    def inject_business_settings():
        settings = None
        try:
            settings = Settings.query.first()
        except Exception:
            settings = None
        cafe_name = (settings.cafe_name if settings and settings.cafe_name else None) or 'Madeline cafe'
        return {
            'settings': settings,
            'global_settings': settings,
            'cafe_name': cafe_name,
        }
    
    # Register Jinja2 filters
    register_jinja_filters(app)
    
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404
    
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
