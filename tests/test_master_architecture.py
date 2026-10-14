import gc
import os
import sqlite3
import tempfile
import unittest

from app import create_app
from config import Config
from models.master_models import CafeEventLog, CafeModule, CafeTenant, CafeWarehouseDefinition, CafeWarehouseProfile, MasterUser, UserCreationRequest
from models.models import Customer, Order, User, db
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
        gc.collect()
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

    def test_restart_preserves_unknown_customer_birth_date(self):
        with self.app.app_context():
            customer = Customer(name="مشتری قدیمی")
            db.session.add(customer)
            db.session.flush()
            db.session.add(Order(
                invoice_number=876543,
                customer_id=customer.id,
                total_amount=100,
                final_amount=100,
            ))
            db.session.commit()
            customer_id = customer.id

        class ReloadConfig(Config):
            TESTING = True
            SECRET_KEY = "test-secret"
            TENANTS_DIR = self.app.config["TENANTS_DIR"]
            SQLALCHEMY_DATABASE_URI = self.app.config["SQLALCHEMY_DATABASE_URI"]
            MASTER_DB_URI = self.app.config["MASTER_DB_URI"]
            SQLALCHEMY_BINDS = {"master": MASTER_DB_URI}
            MASTER_BOOTSTRAP_USERNAME = "admin"
            MASTER_BOOTSTRAP_PASSWORD = "admin"

        reloaded = create_app(ReloadConfig)
        try:
            with reloaded.app_context():
                self.assertIsNone(db.session.get(Customer, customer_id).birth_date)
        finally:
            with reloaded.app_context():
                db.session.remove()
                for engine in db.engines.values():
                    engine.dispose()

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

    def test_cafe_password_login_clears_central_access_in_shared_browser(self):
        with self.app.app_context():
            create_managed_cafe(
                tenants_dir=self.app.config["TENANTS_DIR"],
                name="کافه تست",
                slug="madeline",
                modules=["orders"],
                username="admin",
                password="admin123",
                role="admin",
                user_name="مدیر کافه",
            )

        self.client.post("/master/login", data={"username": "admin", "password": "admin"})
        self.assertEqual(self.client.get("/master/").status_code, 200)

        login = self.client.post(
            "/cafe/madeline/login",
            data={"username": "admin", "password": "admin123"},
        )
        self.assertEqual(login.status_code, 302)
        self.assertEqual(login.headers["Location"], "/cafe/madeline/")
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["tenant_slug"], "madeline")
            self.assertNotIn("master_user_id", browser_session)
        central = self.client.get("/master/", follow_redirects=False)
        self.assertEqual(central.status_code, 302)
        self.assertTrue(central.headers["Location"].startswith("/master/login"))
        self.client.get("/cafe/madeline/logout")

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
        self.assertIn("مشاهده سفارشات", body)
        self.assertNotIn("گزارش مالی", body)
        self.assertEqual(self.client.get('/orders').status_code, 200)
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

    def test_new_cafe_user_request_and_approval_are_tenant_scoped(self):
        self.client.post('/master/login', data={'username': 'admin', 'password': 'admin'})
        created = self.client.post('/master/cafes/create', data={
            'name': 'کافه آزمون معماری',
            'slug': 'architecture-audit',
            'admin_name': 'مدیر آزمون',
            'admin_username': 'manager',
            'admin_password': 'Manager-test-123',
            'admin_role': 'admin',
            'modules': ['orders', 'users', 'reports'],
            'warehouse_mode': 'none',
        })
        self.assertEqual(created.status_code, 302)
        with self.app.app_context():
            cafe = CafeTenant.query.filter_by(slug='architecture-audit').one()
            self.assertTrue(os.path.isfile(cafe.db_path))
            self.assertEqual({m.module_code for m in CafeModule.query.filter_by(cafe_id=cafe.id, is_enabled=True)},
                             {'orders', 'users', 'reports'})

        self.client.post('/cafe/architecture-audit/login', data={
            'username': 'manager', 'password': 'Manager-test-123',
        })
        self.assertEqual(self.client.get('/master/').status_code, 302)
        data = {'username': 'cashier_audit', 'name': 'کاربر آزمون', 'role': 'cashier', 'modal': '1'}
        requested = self.client.post('/admin/users/request', data=data)
        self.assertEqual(requested.status_code, 200)
        self.assertTrue(requested.json['success'])
        self.assertEqual(self.client.post('/admin/users/request', data=data).status_code, 400)
        self.assertEqual(self.client.post('/admin/users/request', data={**data, 'role': 'admin', 'username': 'bad_admin'}).status_code, 400)
        with self.app.app_context():
            req = UserCreationRequest.query.filter_by(username='cashier_audit').one()
            request_id = req.id
            connection = sqlite3.connect(cafe.db_path)
            try:
                self.assertEqual(connection.execute("select count(*) from user where username='cashier_audit'").fetchone()[0], 0)
            finally:
                connection.close()
        self.assertIn('cashier_audit', self.client.get('/admin/users').get_data(as_text=True))

        # The old direct-create endpoint must also enter the approval queue.
        direct = self.client.post('/admin/users/add', data={
            'username': 'waiter_audit', 'password': 'Ignored-123', 'role': 'waiter', 'modal': '1',
        })
        self.assertEqual(direct.status_code, 200)
        with self.app.app_context():
            self.assertEqual(UserCreationRequest.query.filter_by(username='waiter_audit', status='pending').count(), 1)

        self.client.post('/master/login', data={'username': 'admin', 'password': 'admin'})
        approved = self.client.post(f'/master/user-requests/{request_id}/approve')
        self.assertEqual(approved.status_code, 302)
        with self.app.app_context():
            req = UserCreationRequest.query.get(request_id)
            self.assertEqual(req.status, 'approved')
            self.assertIsNone(req.generated_password)
            connection = sqlite3.connect(cafe.db_path)
            try:
                self.assertEqual(connection.execute("select role, is_active from user where username='cashier_audit'").fetchone(),
                                 ('cashier', 1))
            finally:
                connection.close()
        with self.client.session_transaction() as browser_session:
            message = ' '.join(text for _, text in browser_session.get('_flashes', []))
        self.assertIn('رمز اولیه:', message)
        password = message.split('رمز اولیه: ', 1)[1].split(' —', 1)[0]
        self.client.post('/cafe/architecture-audit/login', data={
            'username': 'cashier_audit', 'password': password,
        })
        self.assertEqual(self.client.get('/master/').status_code, 302)
        self.assertEqual(self.client.post('/admin/users/request', data={**data, 'username': 'escalate_audit'}).status_code, 302)
        with self.app.app_context():
            self.assertEqual(UserCreationRequest.query.filter_by(username='escalate_audit').count(), 0)
        deactivated = self.client.post('/master/login', data={'username': 'admin', 'password': 'admin'})
        self.assertEqual(deactivated.status_code, 302)
        self.assertEqual(self.client.post(f'/master/user-requests/{request_id}/deactivate-user').status_code, 302)
        with self.app.app_context():
            self.assertEqual(UserCreationRequest.query.get(request_id).status, 'deactivated')
        self.assertIn('فعال‌سازی دوباره', self.client.get('/master/').get_data(as_text=True))
        self.assertNotEqual(self.client.post('/cafe/architecture-audit/login', data={
            'username': 'cashier_audit', 'password': password,
        }).status_code, 302)
        self.assertEqual(self.client.post(f'/master/user-requests/{request_id}/reactivate-user').status_code, 302)
        with self.client.session_transaction() as browser_session:
            message = ' '.join(text for _, text in browser_session.get('_flashes', []))
        self.assertIn('رمز جدید:', message)
        with self.app.app_context():
            req = UserCreationRequest.query.get(request_id)
            self.assertEqual(req.status, 'approved')
            self.assertIsNone(req.generated_password)

    def test_rejected_request_creates_no_tenant_user(self):
        with self.app.app_context():
            cafe = create_managed_cafe(
                tenants_dir=self.app.config['TENANTS_DIR'], name='رد درخواست', slug='reject-audit',
                modules=['orders', 'users'], username='manager', password='Manager-test-123',
                role='admin', user_name='مدیر',
            )
            cafe_path = cafe.db_path
        self.client.post('/cafe/reject-audit/login', data={'username': 'manager', 'password': 'Manager-test-123'})
        self.assertEqual(self.client.post('/admin/users/request', data={
            'username': 'not_created', 'role': 'waiter', 'modal': '1',
        }).status_code, 200)
        with self.app.app_context():
            request_id = UserCreationRequest.query.filter_by(username='not_created').one().id
        self.client.post('/master/login', data={'username': 'admin', 'password': 'admin'})
        self.assertEqual(self.client.post(f'/master/user-requests/{request_id}/reject').status_code, 302)
        with self.app.app_context():
            self.assertEqual(UserCreationRequest.query.get(request_id).status, 'rejected')
        connection = sqlite3.connect(cafe_path)
        try:
            self.assertEqual(connection.execute("select count(*) from user where username='not_created'").fetchone()[0], 0)
        finally:
            connection.close()
        with self.app.app_context():
            cafe = CafeTenant.query.filter_by(slug='reject-audit').one()
            db.session.add(UserCreationRequest(cafe_id=cafe.id, username='still_pending', role='waiter', status='pending'))
            db.session.commit()
        self.assertEqual(self.client.post('/master/user-requests/delete-all').status_code, 302)
        with self.app.app_context():
            self.assertEqual(UserCreationRequest.query.filter_by(username='not_created').count(), 0)
            self.assertEqual(UserCreationRequest.query.filter_by(username='still_pending', status='pending').count(), 1)

    def test_specialist_roles_cannot_open_other_management_sections(self):
        with self.app.app_context():
            create_managed_cafe(
                tenants_dir=self.app.config['TENANTS_DIR'], name='نقش‌ها', slug='roles-audit',
                modules=['orders', 'inventory', 'accounting', 'reports', 'users', 'menu'],
                username='manager', password='Manager-test-123', role='admin', user_name='مدیر',
                warehouse_mode='central',
            )
        self.client.post('/cafe/roles-audit/login', data={'username': 'manager', 'password': 'Manager-test-123'})
        with self.app.app_context():
            cafe = CafeTenant.query.filter_by(slug='roles-audit').one()
            connection = sqlite3.connect(cafe.db_path)
            try:
                from werkzeug.security import generate_password_hash
                for username, role in [('accountant_test', 'accountant'), ('procurement_test', 'procurement')]:
                    connection.execute(
                        'insert into user (username, password_hash, role, is_active) values (?, ?, ?, 1)',
                        (username, generate_password_hash('Role-test-123'), role),
                    )
                connection.commit()
            finally:
                connection.close()

        self.client.post('/cafe/roles-audit/login', data={'username': 'accountant_test', 'password': 'Role-test-123'})
        self.assertEqual(self.client.get('/admin/financial?period=day').status_code, 200)
        self.assertEqual(self.client.get('/admin/settings').status_code, 302)
        self.assertEqual(self.client.get('/admin/users').status_code, 302)
        self.client.post('/cafe/roles-audit/login', data={'username': 'procurement_test', 'password': 'Role-test-123'})
        self.assertEqual(self.client.get('/admin/inventory').status_code, 200)
        self.assertEqual(self.client.get('/admin/settings').status_code, 302)
        self.assertEqual(self.client.get('/admin/users').status_code, 302)

    def test_deactivated_cafe_expires_existing_employee_session(self):
        with self.app.app_context():
            create_managed_cafe(
                tenants_dir=self.app.config['TENANTS_DIR'], name='کافه تعطیل', slug='inactive-audit',
                modules=['orders'], username='manager', password='Manager-test-123',
                role='admin', user_name='مدیر',
            )
        self.client.post('/cafe/inactive-audit/login', data={
            'username': 'manager', 'password': 'Manager-test-123',
        })
        with self.app.app_context():
            cafe = CafeTenant.query.filter_by(slug='inactive-audit').one()
            cafe.is_active = False
            db.session.commit()
        response = self.client.get('/dashboard/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/cafe/inactive-audit/login')
        with self.client.session_transaction() as browser_session:
            self.assertNotIn('tenant_slug', browser_session)
            self.assertNotIn('_user_id', browser_session)


if __name__ == "__main__":
    unittest.main()
