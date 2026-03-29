"""
app/routes/share.py — Public share card for operative progress.

GET /share/<username>   — renders the share card (HTML, no login needed)
GET /share/me           — shortcut for current user's card (login required)

The share card is a standalone page with no sidebar/nav, designed to
look good as a screenshot. It shows: title, streak, productivity score,
level, and top achievements.
"""
from flask import render_template, abort, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app.services.data_context import DataContext
from app.services.identity_service import get_operative_title
from app.services.analytics_service import (
    task_analytics, habit_analytics, wellness_analytics, productivity_score
)
from app.extensions import limiter
from . import Blueprint

share_bp = Blueprint('share', __name__)


@share_bp.route('/share/me', endpoint='share_me')
@login_required
def share_me():
    return redirect(url_for('share.share_card', username=current_user.username))


@share_bp.route('/share/<username>', endpoint='share_card')
@limiter.limit('60 per minute; 200 per hour')
def share_card(username: str):
    user = User.query.filter(
        User.username.ilike(username)
    ).first()
    if not user:
        abort(404)

    # Build DataContext — analytics functions require a ctx, not a raw User
    ctx = DataContext.build(user)

    # Compute everything needed for the card
    t_data = task_analytics(ctx)
    h_data = habit_analytics(ctx)
    w_data = wellness_analytics(ctx)
    prod   = productivity_score(ctx, t_data, h_data, w_data)
    title  = get_operative_title(user)

    # Top 3 achievements for display
    top_ach = user.achievements.order_by(
        __import__('app.models.achievement', fromlist=['UserAchievement']).UserAchievement.unlocked_at.desc()
    ).limit(3).all()

    return render_template('share.html',
        share_user=user, title=title, prod=prod,
        t_data=t_data, h_data=h_data, w_data=w_data,
        top_ach=top_ach,
    )
