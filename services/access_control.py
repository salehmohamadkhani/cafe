from __future__ import annotations

from flask import g, has_request_context, session


def is_master_sso() -> bool:
    """Return whether this request carries a consistent master-to-tenant SSO context."""
    if has_request_context() and hasattr(g, '_master_sso_valid'):
        return bool(g._master_sso_valid)
    master_id = session.get('master_user_id')
    sso_master_id = session.get('tenant_sso_master_user_id')
    structurally_valid = bool(
        master_id
        and session.get('tenant_slug')
        and session.get('tenant_auth_source') == 'master_sso'
        and str(master_id) == str(sso_master_id)
    )
    if not structurally_valid:
        if has_request_context():
            g._master_sso_valid = False
        return False

    from models.master_models import MasterUser
    try:
        valid = MasterUser.query.filter_by(id=int(master_id), is_active=True).first() is not None
    except (TypeError, ValueError):
        valid = False
    if has_request_context():
        g._master_sso_valid = valid
    return valid


def effective_role(user=None) -> str | None:
    """Resolve authorization role without mutating the tenant user's stored role."""
    if is_master_sso():
        return 'superadmin'
    return getattr(user, 'role', None) if user is not None else None


def role_is(user, *roles: str) -> bool:
    return effective_role(user) in set(roles)
