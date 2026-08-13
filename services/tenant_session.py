from __future__ import annotations

from flask import session
from flask_login import login_user


def establish_tenant_session(
    *,
    cafe,
    user,
    remember: bool = False,
    master_user_id: int | None = None,
) -> None:
    """Create the canonical Flask session for a tenant user.

    A master SSO session intentionally keeps ``master_user_id`` so the operator
    can return to the command center without authenticating again.
    """
    session['tenant_slug'] = cafe.slug
    session['tenant_db_path'] = cafe.db_path
    session['tenant_user_id'] = int(user.id)
    session['tenant_username'] = user.username

    if master_user_id is not None:
        session['tenant_auth_source'] = 'master_sso'
        session['tenant_sso_master_user_id'] = int(master_user_id)
    else:
        session['tenant_auth_source'] = 'password'
        session.pop('tenant_sso_master_user_id', None)

    login_user(user, remember=remember)


def clear_tenant_session(*, keep_master: bool = True) -> None:
    """Clear tenant authentication while optionally preserving master access."""
    from flask_login import logout_user

    logout_user()
    for key in (
        'tenant_slug',
        'tenant_db_path',
        'tenant_user_id',
        'tenant_username',
        'tenant_auth_source',
        'tenant_sso_master_user_id',
    ):
        session.pop(key, None)
    if not keep_master:
        session.pop('master_user_id', None)
