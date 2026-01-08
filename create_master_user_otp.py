#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ایجاد یا به‌روزرسانی کاربر master با شماره موبایل
برای استفاده با سیستم OTP
"""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import db
from models.master_models import MasterUser


def _create_all_master_tables():
    """Flask-SQLAlchemy create_all signature differs across versions."""
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
    phone_number = (os.environ.get("MASTER_PHONE") or "").strip() or "09121148277"
    
    # نرمال‌سازی شماره موبایل
    phone_normalized = phone_number.replace(' ', '').replace('-', '').replace('+', '')
    if phone_normalized.startswith('0'):
        phone_normalized = '98' + phone_normalized[1:]
    elif not phone_normalized.startswith('98'):
        phone_normalized = '98' + phone_normalized
    
    app = create_app()
    with app.app_context():
        _create_all_master_tables()
        
        existing = MasterUser.query.filter_by(phone_number=phone_normalized).first()
        if existing:
            print(f"✅ کاربر master با شماره {phone_number} از قبل وجود دارد.")
            print(f"   ID: {existing.id}")
            print(f"   Role: {existing.role}")
            print(f"   Active: {existing.is_active}")
        else:
            user = MasterUser(
                phone_number=phone_normalized,
                username=phone_normalized,
                role="superadmin",
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            print(f"✅ کاربر master با شماره {phone_number} ایجاد شد.")
            print(f"   ID: {user.id}")
            print(f"   Phone: {user.phone_number}")
            print(f"   Role: {user.role}")
        
        print("\n➡️ حالا می‌توانید با شماره موبایل وارد شوید:")
        print(f"   /master/login")


if __name__ == "__main__":
    main()

