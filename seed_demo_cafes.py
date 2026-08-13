from app import create_app
from models.master_models import CafeTenant
from services.master_service import DEMO_CAFES, ensure_master_admin, seed_demo_cafes


def main() -> None:
    app = create_app()
    with app.app_context():
        ensure_master_admin(
            app.config["MASTER_BOOTSTRAP_USERNAME"],
            app.config["MASTER_BOOTSTRAP_PASSWORD"],
        )
        created = seed_demo_cafes(app.config["TENANTS_DIR"])
        print(f"created={len(created)} total={CafeTenant.query.count()}")
        for demo in DEMO_CAFES:
            print(f"{demo.slug}: {demo.username} / {demo.password} ({demo.role})")


if __name__ == "__main__":
    main()
