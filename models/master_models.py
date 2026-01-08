from __future__ import annotations

from datetime import datetime

from models.models import db


class MasterUser(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'master_user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=True, index=True)  # Now nullable, phone is primary
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)  # Primary identifier
    password_hash = db.Column(db.String(256), nullable=True)  # Now nullable for OTP-only users
    role = db.Column(db.String(32), nullable=False, default='superadmin')  # superadmin, support, ...
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<MasterUser {self.phone_number} ({self.role})>"


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


class CafeModule(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'cafe_module'

    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey('cafe_tenant.id'), nullable=False, index=True)
    module_code = db.Column(db.String(64), nullable=False, index=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('cafe_id', 'module_code', name='uq_cafe_module'),)

    def __repr__(self) -> str:
        return f"<CafeModule cafe_id={self.cafe_id} module_code={self.module_code} enabled={self.is_enabled}>"


class CafeEventLog(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'cafe_event_log'

    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey('cafe_tenant.id'), nullable=False, index=True)
    event_type = db.Column(db.String(128), nullable=False, index=True)
    payload_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CafeEventLog cafe_id={self.cafe_id} event_type={self.event_type}>"


class OTPCode(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'otp_code'

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)  # 6-digit OTP
    is_used = db.Column(db.Boolean, nullable=False, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<OTPCode {self.phone_number} {self.code} (used={self.is_used})>"


class UserCreationRequest(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'user_creation_request'

    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey('cafe_tenant.id'), nullable=False, index=True)
    requested_by = db.Column(db.String(128), nullable=True)  # نام کاربری که درخواست داده
    username = db.Column(db.String(64), nullable=False)  # نام کاربری درخواستی
    name = db.Column(db.String(128), nullable=True)  # نام و نام خانوادگی
    phone = db.Column(db.String(20), nullable=True)  # شماره تماس
    role = db.Column(db.String(32), nullable=False, default='cashier')  # نقش درخواستی
    status = db.Column(db.String(32), nullable=False, default='pending')  # pending, approved, rejected
    generated_username = db.Column(db.String(64), nullable=True)  # نام کاربری تولید شده
    generated_password = db.Column(db.String(128), nullable=True)  # رمز عبور تولید شده
    approved_by = db.Column(db.Integer, db.ForeignKey('master_user.id'), nullable=True)  # کسی که تایید کرده
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)  # یادداشت‌های اضافی

    def __repr__(self) -> str:
        return f"<UserCreationRequest cafe_id={self.cafe_id} username={self.username} status={self.status}>"
