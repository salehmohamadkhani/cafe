from __future__ import annotations

from datetime import datetime

from models.models import db


class MasterUser(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'master_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='superadmin')  # superadmin, support, ...
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<MasterUser {self.username} ({self.role})>"


class CafeTenant(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'cafe_tenant'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # Where this cafe lives on disk + where its sqlite DB is stored
    root_dir = db.Column(db.String(512), nullable=False)
    db_path = db.Column(db.String(512), unique=True, nullable=False)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CafeTenant {self.slug} ({self.name})>"

