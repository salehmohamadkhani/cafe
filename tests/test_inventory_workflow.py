from datetime import date
import tempfile
import unittest

from config import Config
from app import create_app
from models.models import (
    db, Category, Customer, MaterialPurchase, MenuItem, MenuItemMaterial, Order, OrderItem,
    RawMaterial, RawMaterialUsage, Warehouse, convert_unit,
    sync_order_item_material_usage,
)


class InventoryWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

        class WorkflowConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.tmp.name}/app.db"
            SQLALCHEMY_BINDS = {'master': f"sqlite:///{self.tmp.name}/master.db"}
            TESTING = True
            SECRET_KEY = 'workflow-test'
            TENANTS_DIR = f"{self.tmp.name}/tenants"
            MASTER_BOOTSTRAP_USERNAME = 'admin'
            MASTER_BOOTSTRAP_PASSWORD = 'admin'

        self.app = create_app(WorkflowConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.drop_all(bind_key='master')
        db.create_all()
        db.create_all(bind_key='master')

    def tearDown(self):
        db.session.remove()
        for engine in db.engines.values():
            engine.dispose()
        self.ctx.pop()
        self.tmp.cleanup()

    def test_weighted_average_normalizes_purchase_units(self):
        material = RawMaterial(name='آرد', default_unit='gr')
        central = Warehouse(code='central', name='انبار مرکزی')
        waste = Warehouse(code='waste', name='انبار ضایعات')
        db.session.add_all([material, central, waste])
        db.session.flush()
        db.session.add_all([
            MaterialPurchase(raw_material_id=material.id, purchase_date=date.today(), quantity=3, unit='kg', total_price=500_000, warehouse_id=central.id),
            MaterialPurchase(raw_material_id=material.id, purchase_date=date.today(), quantity=2, unit='kg', total_price=600_000, warehouse_id=waste.id),
        ])
        db.session.commit()
        self.assertEqual(convert_unit(5, 'kg', 'gr'), 5000)
        self.assertAlmostEqual(material.weighted_average_unit_price, 220.0)
        self.assertAlmostEqual(material.latest_unit_price, 300.0)

    def test_deleted_order_item_releases_material_usage(self):
        material = RawMaterial(name='قهوه', default_unit='gr')
        category = Category(name='بار گرم', is_active=True)
        customer = Customer(name='مشتری تست', phone='09120000000')
        db.session.add_all([material, category, customer])
        db.session.flush()
        menu_item = MenuItem(name='اسپرسو', price=100_000, is_active=True, category_id=category.id)
        db.session.add(menu_item)
        db.session.flush()
        db.session.add(MenuItemMaterial(menu_item_id=menu_item.id, raw_material_id=material.id, name='قهوه', quantity='18', unit='gr'))
        order = Order(invoice_number=9999, customer_id=customer.id, type='بیرون‌بر', status='پرداخت نشده', total_amount=100_000, final_amount=100_000)
        db.session.add(order)
        db.session.flush()
        item = OrderItem(order_id=order.id, menu_item_id=menu_item.id, quantity=2, unit_price=100_000, total_price=200_000)
        db.session.add(item)
        db.session.flush()
        sync_order_item_material_usage(item)
        db.session.commit()
        self.assertAlmostEqual(RawMaterialUsage.query.filter_by(order_item_id=item.id).first().quantity, 36)

        item.is_deleted = True
        sync_order_item_material_usage(item)
        db.session.commit()
        self.assertEqual(RawMaterialUsage.query.filter_by(order_item_id=item.id).count(), 0)


if __name__ == '__main__':
    unittest.main()
