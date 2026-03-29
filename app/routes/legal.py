"""
app/routes/legal.py — Privacy Policy and Terms of Use.
"""
from flask import render_template
from . import Blueprint

legal_bp = Blueprint('legal', __name__)


@legal_bp.route('/privacy', endpoint='privacy')
def privacy():
    return render_template('legal/privacy.html')


@legal_bp.route('/terms', endpoint='terms')
def terms():
    return render_template('legal/terms.html')
