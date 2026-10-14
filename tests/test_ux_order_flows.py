import gc
import os
import tempfile
import unittest
from datetime import datetime

import pytz

from app import create_app
from config import Config
from models.models import db
from services.master_service import seed_demo_cafes


class OrderUxFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="cafe-order-ux-")
        root = self.temp_dir.name
        os.makedirs(os.path.join(root, "instance"), exist_ok=True)

        class TestConfig(Config):
            TESTING = True
            SECRET_KEY = "order-ux-test"
            TENANTS_DIR = os.path.join(root, "tenants")
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(root, 'instance', 'cafe.db')}"
            MASTER_DB_URI = f"sqlite:///{os.path.join(root, 'instance', 'master.db')}"
            SQLALCHEMY_BINDS = {"master": MASTER_DB_URI}
            MASTER_BOOTSTRAP_USERNAME = "audit"
            MASTER_BOOTSTRAP_PASSWORD = "audit-password"

        self.app = create_app(TestConfig)
        with self.app.app_context():
            seed_demo_cafes(self.app.config["TENANTS_DIR"])
        self.client = self.app.test_client()
        login = self.client.post(
            "/cafe/madeline/login", data={"username": "admin", "password": "admin123"}
        )
        self.assertEqual(login.status_code, 302)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            for engine in db.engines.values():
                engine.dispose()
        gc.collect()
        self.temp_dir.cleanup()

    def test_direct_new_order_page_and_ajax_modal_both_render(self):
        direct = self.client.get("/order/new")
        ajax = self.client.get(
            "/order/new", headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(direct.status_code, 200)
        self.assertIn(b'id="new-order-full-page"', direct.data)
        self.assertIn(b'id="order-form"', direct.data)
        self.assertEqual(ajax.status_code, 200)
        self.assertNotIn(b'id="new-order-full-page"', ajax.data)
        self.assertIn(b'id="order-form"', ajax.data)

    def test_order_submission_opens_detail_and_same_day_filter_keeps_it(self):
        item = self.client.post(
            "/menu/save", json={"name": "UX test tea", "price": 120000, "stock": 10}
        )
        self.assertEqual(item.status_code, 200)
        item_id = item.json["item"]["id"]

        saved = self.client.post(
            "/order",
            data={
                "customer_name": "UX test customer",
                "item": str(item_id),
                "quantity": "1",
                "discount": "0",
            },
        )
        self.assertEqual(saved.status_code, 302)
        self.assertRegex(saved.headers["Location"], r"/order/\d+$")
        detail = self.client.get(saved.headers["Location"])
        self.assertEqual(detail.status_code, 200)
        self.assertIn("UX test customer", detail.get_data(as_text=True))

        today = datetime.now(pytz.timezone("Asia/Tehran")).date().isoformat()
        report = self.client.get(f"/admin/orders?from={today}&to={today}")
        self.assertEqual(report.status_code, 200)
        self.assertIn("UX test customer", report.get_data(as_text=True))

    def test_legacy_menu_add_link_uses_live_menu_and_saves_valid_item(self):
        page = self.client.get("/menu/item/add", follow_redirects=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn("مدیریت منو", page.get_data(as_text=True))
        saved = self.client.post(
            "/menu/item/add", data={"name": "Legacy tea", "price": "45000", "stock": "2"},
            follow_redirects=True,
        )
        self.assertEqual(saved.status_code, 200)
        self.assertIn("Legacy tea", saved.get_data(as_text=True))

    def test_primary_cafe_sections_render_without_server_errors(self):
        paths = (
            "/dashboard/", "/menu", "/menu/price-management", "/orders",
            "/admin/settings", "/admin/users", "/admin/inventory",
            "/admin/warehouses", "/admin/financial",
            "/admin/customers/leaderboard", "/admin/orders",
        )
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=True)
                self.assertEqual(response.status_code, 200, response.headers.get("Location"))
                self.assertIn(b"<html", response.data.lower())


if __name__ == "__main__":
    unittest.main()
