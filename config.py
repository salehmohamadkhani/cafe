import os
import secrets

class Config:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASEDIR, 'instance')
    TENANTS_DIR = os.environ.get('CAFE_TENANTS_DIR') or os.path.join(BASEDIR, 'tenants')

    # SECRET_KEY:
    # - Prefer environment variable (recommended for production)
    # - Otherwise persist one in instance/secret_key so sessions survive restarts
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        secret_path = os.path.join(INSTANCE_DIR, 'secret_key')
        try:
            with open(secret_path, 'r', encoding='utf-8') as f:
                SECRET_KEY = f.read().strip() or None
        except FileNotFoundError:
            SECRET_KEY = None
        except Exception:
            SECRET_KEY = None

        if not SECRET_KEY:
            try:
                os.makedirs(INSTANCE_DIR, exist_ok=True)
                SECRET_KEY = secrets.token_urlsafe(48)
                with open(secret_path, 'w', encoding='utf-8') as f:
                    f.write(SECRET_KEY)
                try:
                    os.chmod(secret_path, 0o600)
                except Exception:
                    pass
            except Exception:
                # Fallback (non-persistent) if filesystem is not writable
                SECRET_KEY = secrets.token_urlsafe(48)

    # Default (single-cafe) database
    # NOTE: We intentionally do NOT read generic DATABASE_URL here, because
    # this project is commonly deployed as SQLite and some server environments
    # may set DATABASE_URL for other apps (which would break startup).
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('CAFE_DB_URI')
        or f"sqlite:///{os.path.join(INSTANCE_DIR, 'cafe.db')}"
    )

    # Master database (multi-cafe admin portal)
    MASTER_DB_URI = (
        os.environ.get('CAFE_MASTER_DB_URI')
        or f"sqlite:///{os.path.join(INSTANCE_DIR, 'master.db')}"
    )
    SQLALCHEMY_BINDS = {
        'master': MASTER_DB_URI
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False