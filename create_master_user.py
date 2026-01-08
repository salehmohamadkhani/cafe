#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from getpass import getpass

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import db
from models.master_models import MasterUser
from werkzeug.security import generate_password_hash


def _create_all_master_tables():
    """
    Flask-SQLAlchemy create_all signature differs across versions.
    We try the known variants to ensure master tables exist.
    """
    try:
        db.create_all(bind_key="master")
        return
    except TypeError:
        pass
    try:
        db.create_all(bind="master")
        return
    except TypeError:
        pass
    # Fallback: create all binds
    db.create_all()


def main():
    username = (os.environ.get("MASTER_USERNAME") or "").strip() or "master"
    password = os.environ.get("MASTER_PASSWORD")

    if not password:
        password = getpass("Enter password for master user: ").strip()
        if len(password) < 8:
            print("❌ Password too short (min 8 chars).")
            sys.exit(1)

    app = create_app()
    with app.app_context():
        _create_all_master_tables()

        existing = MasterUser.query.filter_by(username=username).first()
        if existing:
            # Update password (safe default for bootstrap)
            existing.password_hash = generate_password_hash(password)
            db.session.commit()
            print(f"✅ Master user existed. Password updated. username={username}")
        else:
            u = MasterUser(
                username=username,
                password_hash=generate_password_hash(password),
                role="superadmin",
                is_active=True,
            )
            db.session.add(u)
            db.session.commit()
            print(f"✅ Master user created. username={username}")

        print("➡️ Now open: /master/login  (or /login)")


if __name__ == "__main__":
    main()

