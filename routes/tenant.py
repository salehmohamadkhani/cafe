from __future__ import annotations

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, session, url_for

from models.master_models import CafeTenant


tenant_bp = Blueprint('tenant', __name__, url_prefix='/cafe/<slug>')


def require_tenant_session(view_func):
    """Require an active cafe and a session scoped to the URL tenant."""
    @wraps(view_func)
    def wrapper(slug, *args, **kwargs):
        cafe = CafeTenant.query.filter_by(slug=slug).first()
        if not cafe:
            flash('کافه یافت نشد.', 'danger')
            session.pop('tenant_slug', None)
            return redirect(url_for('master.dashboard'))
        if not cafe.is_active:
            for key in ('tenant_slug', 'tenant_db_path', 'tenant_user_id', 'tenant_username'):
                session.pop(key, None)
            return render_template('tenant/inactive.html', cafe=cafe), 403
        if session.get('tenant_slug') != slug:
            flash('لطفاً ابتدا وارد کافه شوید.', 'warning')
            return redirect(url_for('tenant_auth.login', slug=slug))
        return view_func(slug, *args, **kwargs)
    return wrapper


@tenant_bp.route('/')
@require_tenant_session
def dashboard(slug):
    """Canonical cafe entrypoint; all tenants use the shared dashboard route."""
    return redirect(url_for('dashboard.dashboard'))


@tenant_bp.route('/dashboard/')
@tenant_bp.route('/dashboard')
@require_tenant_session
def dashboard_full(slug):
    """Compatibility URL for bookmarks created before dashboard unification."""
    return redirect(url_for('dashboard.dashboard'))
