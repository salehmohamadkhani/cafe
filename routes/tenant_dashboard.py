from __future__ import annotations

import os
import sys
from flask import Blueprint, redirect, url_for, current_app
from models.master_models import CafeTenant

tenant_dashboard_bp = Blueprint('tenant_dashboard', __name__)


@tenant_dashboard_bp.route('/cafe/<slug>/dashboard/')
@tenant_dashboard_bp.route('/cafe/<slug>/dashboard')
def redirect_to_tenant_dashboard(slug):
    """Redirect to tenant's own dashboard (which runs as separate project)"""
    cafe = CafeTenant.query.filter_by(slug=slug).first_or_404()
    
    if not cafe.is_active:
        return redirect(url_for('master.dashboard'))
    
    if not os.path.exists(cafe.root_dir):
        return redirect(url_for('master.dashboard'))
    
    # Check if tenant has its own wsgi.py
    tenant_wsgi = os.path.join(cafe.root_dir, 'wsgi.py')
    if not os.path.exists(tenant_wsgi):
        return redirect(url_for('master.dashboard'))
    
    # For now, redirect to tenant login if not authenticated
    # Later we can set up separate nginx configs for each tenant
    return redirect(url_for('tenant_auth.login', slug=slug))
