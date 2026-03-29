"""
app/routes/entrance.py — Public landing page (/).

Routing logic:
  logged-in  → redirect to /dashboard
  logged-out → render the landing page
"""
from flask import render_template, redirect, url_for
from flask_login import current_user
from app.extensions import limiter
from . import Blueprint

entrance_bp = Blueprint('entrance', __name__)


@entrance_bp.route('/', endpoint='entrance')
@limiter.limit('120 per minute')
def entrance():
    # Authenticated users go straight to their dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    return render_template('entrance.html')
