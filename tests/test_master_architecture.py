import os
import sqlite3
import tempfile
import unittest

from app import create_app
from config import Config
from models.master_models import CafeEventLog, CafeModule, CafeTenant, CafeWarehouseDefinition, CafeWarehouseProfile, MasterUser
from models.models import db
from services.master_service import create_managed_cafe, seed_demo_cafes


class MasterArchitectureTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="cafe-master-test-")
        root = self.temp_dir.name
        instance_dir = os.path.join(root, "instance")
        os.makedirs(instance_dir, exist_ok=True)

        class TestConfig(Config):
            TESTING = True
            SECRET_KEY = "test-secret"
            TENANTS_DIR = os.path.join(root, "tenants")
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(instance_dir, 'cafe.db')}"
            MASTER_DB_URI = f"sqlite:///{os.path.join(instance_dir, 'master.db')}"
            SQLALCHEMY_BINDS = {"master": MASTER_DB_URI}
            MASTER_BOOTSTRAP_USERNAME = "admin"
            MASTER_BOOTSTRAP_PASSWORD = "admin"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            for engine in db.engines.values():
                engine.dispose()
        self.temp_dir.cleanup()

    def test_master_login_is_hashed_and_requires_correct_password(self):
        with self.app.app_context():
            master = MasterUser.query.filter_by(username="admin").one()
            self.assertNotEqual(master.password_hash, "admin")
            self.assertTrue(master.password_hash)

        wrong = self.client.post("/master/login", data={"username": "admin", "password": "wrong"})
        correct = self.client.post("/master/login", data={"username": "admin", "password": "admin"})
        self.assertEqual(wrong.status_code, 200)
        self.assertEqual(correct.status_code, 302)
        self.assertEqual(correct.headers["Location"], "/master/")

    def test_demo_cafes_use_shared_code_and_isolated_databases(self):
        with self.app.app_context():
            created = seed_demo_cafes(self.app.config["TENANTS_DIR"])
            self.assertEqual(len(created), 3)
            self.assertEqual(CafeTenant.query.count(), 3)
            self.assertEqual(CafeModule.query.count(), 21)
            paths = {cafe.db_path for cafe in CafeTenant.query.all()}
            self.assertEqual(len(paths), 3)
            for cafe in CafeTenant.query.all():
                self.assertTrue(os.path.isfile(cafe.db_path))
                self.assertFalse(os.path.exists(os.path.join(cafe.root_dir, "app.py")))
                connection = sqlite3.connect(cafe.db_path)
                try:
                    self.assertEqual(connection.execute("pragma integrity_check").fetchone()[0], "ok")
                finally:
                    connection.close()

    def test_master_modules_block_disabled_tenant_features(self):
        with self.app.app_context():
            seed_demo_cafes(self.app.config["TENANTS_DIR"])

        login = self.client.post(
            "/cafe/kiosk/login",
            data={"username": "cashier", "password": "cashier123"},
        )
        blocked = self.client.get("/admin/inventory", follow_redirects=False)
        self.assertEqual(login.status_code, 302)
        self.assertEqual(blocked.status_code, 302)
        self.assertEqual(blocked.headers["Location"], "/cafe/kiosk/")

    def test_warehouse_topologies_are_provisioned_in_master_and_tenant_databases(self):
        with self.app.app_context():
            cafe = create_managed_cafe(
                tenants_dir=self.app.config["TENANTS_DIR"],
                name="کافه چند انباره",
                slug="multi-store",
                modules=["orders", "inventory"],
                username="manager",
                password="manager123",
                role="admin",
                user_name="مدیر تست",
                warehouse_mode="multi",
                warehouse_names=["انبار مرکزی", "انبار آشپزخانه", "انبار بار"],
            )
            profile = CafeWarehouseProfile.query.filter_by(cafe_id=cafe.id).one()
            definitions = CafeWarehouseDefinition.query.filter_by(cafe_id=cafe.id).all()
            self.assertEqual(profile.mode, "multi")
            self.assertEqual(len(definitions), 3)

            connection = sqlite3.connect(cafe.db_path)
            try:
                config = connection.execute(
                    "select is_enabled, warehouse_mode from inventory_configuration"
                ).fetchone()
                warehouses = connection.execute("select code, name from warehouse order by id").fetchall()
            finally:
                connection.close()
            self.assertEqual(config, (1, "multi"))
            self.assertEqual([name for _, name in warehouses], ["انبار مرکزی", "انبار آشپزخانه", "انبار بار"])

    def test_inventory_disabled_forces_no_warehouse_topology(self):
        with self.app.app_context():
            cafe = create_managed_cafe(
                tenants_dir=self.app.config["TENANTS_DIR"],
                name="کافه فروش",
                slug="sales-only",
                modules=["orders"],
                username="cashier",
                password="cashier123",
                role="cashier",
                user_name="صندوق‌دار",
                warehouse_mode="multi",
                warehouse_names=["انبار اول", "انبار دوم"],
            )
            profile = CafeWarehouseProfile.query.filter_by(cafe_id=cafe.id).one()
            self.assertEqual(profile.mode, "none")
            self.assertEqual(CafeWarehouseDefinition.query.filter_by(cafe_id=cafe.id).count(), 0)

    def test_operational_queries_are_routed_to_the_logged_in_tenant(self):
        with self.app.app_context():
            seed_demo_cafes(self.app.config["TENANTS_DIR"])

        login = self.client.post(
            "/cafe/madeline/login",
            data={"username": "admin", "password": "admin123"},
        )
        response = self.client.get("/admin/warehouses")
        body = response.get_data(as_text=True)
        self.assertEqual(login.status_code, 302)
        self.assertEqual(response.status_code, 200)
        self.assertIn("انبار بار و سرویس", body)
        self.assertNotIn("انبار قلیان", body)

    def test_master_access_view_exposes_the_canonical_warehouse_profile(self):
        with self.app.app_context():
            seed_demo_cafes(self.app.config["TENANTS_DIR"])
        self.client.post("/master/login", data={"username": "admin", "password": "admin"})
        response = self.client.get("/master/cafes/madeline/access")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("WAREHOUSE TOPOLOGY", body)
        self.assertIn("انبار بار و سرویس", body)

    def test_master_can_enter_tenant_without_password_and_return(self):
        with self.app.app_context():
            seed_demo_cafes(self.app.config["TENANTS_DIR"])

        self.client.post("/master/login", data={"username": "admin", "password": "admin"})
        entered = self.client.get("/master/cafes/madeline/enter", follow_redirects=False)
        self.assertEqual(entered.status_code, 302)
        self.assertEqual(entered.headers["Location"], "/cafe/madeline/")

        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["master_user_id"], 1)
            self.assertEqual(browser_session["tenant_slug"], "madeline")
            self.assertEqual(browser_session["tenant_auth_source"], "master_sso")
            self.assertEqual(browser_session["tenant_sso_master_user_id"], 1)

        dashboard = self.client.get("/cafe/madeline/dashboard", follow_redirects=True)
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("داشبورد لحظه‌ای کافه", dashboard.get_data(as_text=True))
        self.assertIn("حالت نظارت مرکزی فعال است", dashboard.get_data(as_text=True))
        self.assertIn("بازگشت به مرکز فرمان", dashboard.get_data(as_text=True))

        returned = self.client.get("/master/return-from-cafe", follow_redirects=False)
        self.assertEqual(returned.status_code, 302)
        self.assertEqual(returned.headers["Location"], "/master/")
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["master_user_id"], 1)
            self.assertNotIn("tenant_slug", browser_session)
            self.assertNotIn("_user_id", browser_session)

        with self.app.app_context():
            event = CafeEventLog.query.filter_by(event_type="cafe.master_sso.entered").one()
            self.assertIn('"tenant_username": "admin"', event.payload_json)

    def test_master_sso_overrides_local_role_and_module_limits_without_mutating_them(self):
        with self.app.app_context():
            seed_demo_cafes(self.app.config["TENANTS_DIR"])
            roastery = CafeTenant.query.filter_by(slug="roastery").one()
            configured_modules = {
                row.module_code for row in CafeModule.query.filter_by(cafe_id=roastery.id, is_enabled=True)
            }
            self.assertNotIn("orders", configured_modules)
            self.assertNotIn("accounting", configured_modules)

        self.client.post("/master/login", data={"username": "admin", "password": "admin"})
        entered = self.client.get("/master/cafes/roastery/enter", follow_redirects=True)
        self.assertEqual(entered.status_code, 200)
        self.assertIn("داشبورد لحظه‌ای کافه", entered.get_data(as_text=True))
        self.assertNotIn("انباردار فقط", entered.get_data(as_text=True))

        self.assertEqual(self.client.get("/menu").status_code, 200)
        self.assertEqual(self.client.get("/admin/inventory").status_code, 200)
        self.assertEqual(self.client.get("/admin/financial?period=month").status_code, 200)

        with self.app.app_context():
            roastery = CafeTenant.query.filter_by(slug="roastery").one()
            configured_modules_after = {
                row.module_code for row in CafeModule.query.filter_by(cafe_id=roastery.id, is_enabled=True)
            }
            self.assertEqual(configured_modules_after, configured_modules)

    def test_tenant_navigation_reflects_configured_modules_outside_master_sso(self):
        with self.app.app_context():
            seed_demo_cafes(self.app.config["TENANTS_DIR"])
        self.client.post(
            "/cafe/kiosk/login",
            data={"username": "cashier", "password": "cashier123"},
        )
        dashboard = self.client.get("/dashboard/")
        body = dashboard.get_data(as_text=True)
        self.assertEqual(dashboard.status_code, 200)
        # Cashiers operate from the POS dashboard; management links should not
        # be advertised only to redirect them after the click.
        self.assertNotIn("مشاهده منو", body)
        self.assertIn("گزارش مالی", body)
        self.assertNotIn("مدیریت انبارها", body)
        self.assertNotIn("حالت نظارت مرکزی فعال است", body)

    def test_deactivated_master_account_expires_supervisory_tenant_session(self):
        with self.app.app_context():
            seed_demo_cafes(self.app.config["TENANTS_DIR"])
        self.client.post("/master/login", data={"username": "admin", "password": "admin"})
        self.client.get("/master/cafes/madeline/enter")

        with self.app.app_context():
            master = MasterUser.query.filter_by(username="admin").one()
            master.is_active = False
            db.session.commit()

        expired = self.client.get("/dashboard/", follow_redirects=False)
        self.assertEqual(expired.status_code, 302)
        self.assertTrue(expired.headers["Location"].startswith("/master/login"))
        with self.client.session_transaction() as browser_session:
            self.assertNotIn("tenant_slug", browser_session)
            self.assertNotIn("master_user_id", browser_session)


if __name__ == "__main__":
    unittest.main()
