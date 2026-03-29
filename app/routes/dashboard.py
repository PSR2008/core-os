"""
app/routes/dashboard.py — Dashboard.

DataContext.build() runs ~12 DB queries total.
All analytics, insights, identity, and suggestions consume ctx — zero
additional DB calls beyond what DataContext already loaded.
Total dashboard DB queries: ~12.
"""
import datetime as _dt
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user

from app.services.data_context        import DataContext
from app.services.analytics_service   import (
    task_analytics, habit_analytics, expense_analytics,
    wellness_analytics, xp_analytics, productivity_score,
    get_suggestions, get_reminders,
)
from app.services.game_service         import compute_threat_score, user_stats, shared_ctx
from app.services.achievement_service  import get_progress_hints, get_achievement_summary
from app.services.insights_service     import generate_insights
from app.services.identity_service     import get_operative_title
from app.services.feedback_service     import get_feedback_banners
from app.services.growth_service       import track
from app.services.referral_service     import get_referral_stats
from . import Blueprint

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard', endpoint='index')
@login_required
def index():
    u = current_user

    # ── Streak + housekeeping ──────────────────────────────────────────────────
    u.update_login_streak()
    track('dau', user_id=u.id)
    u.ensure_referral_code()

    # Redirect incomplete onboarders
    if not u.onboarding_complete:
        return redirect(url_for('growth.onboarding'))

    # ── Single bulk DB load (replaces ~180 individual queries) ─────────────────
    ctx = DataContext.build(u)

    # ── Pure-Python analytics (zero DB after this point) ──────────────────────
    t_data  = task_analytics(ctx)
    h_data  = habit_analytics(ctx)
    e_data  = expense_analytics(ctx)
    w_data  = wellness_analytics(ctx)
    x_data  = xp_analytics(ctx)
    prod    = productivity_score(ctx, t_data, h_data, w_data)
    threat  = compute_threat_score(u, ctx)

    # ── Intelligence (uses ctx data — no extra queries) ────────────────────────
    insights    = generate_insights(u, ctx)
    suggestions = get_suggestions(ctx, t_data, h_data, w_data)
    reminders   = get_reminders(ctx)

    # ── Identity + emotional feedback ─────────────────────────────────────────
    identity = get_operative_title(u, ctx)
    banners  = get_feedback_banners(u, t_data, h_data, w_data)

    # ── Achievements ──────────────────────────────────────────────────────────
    hints               = get_progress_hints(u, ctx)
    ach_summary         = get_achievement_summary(u)
    recent_achievements = u.achievements.order_by(
        __import__('app.models.achievement', fromlist=['UserAchievement']).UserAchievement.unlocked_at.desc()
    ).limit(3).all()

    is_new_user = (t_data['total'] == 0 and h_data['total'] == 0)

    hour = _dt.datetime.now().hour
    if hour < 12:   greeting = 'Good morning'
    elif hour < 17: greeting = 'Good afternoon'
    elif hour < 21: greeting = 'Good evening'
    else:           greeting = 'Late night session'

    name = u.operative_name or u.username

    return render_template('index.html',
        # Intelligence
        suggestions=suggestions, reminders=reminders, insights=insights,
        # Identity + emotional
        identity=identity, banners=banners,
        # Analytics
        t_data=t_data, h_data=h_data, e_data=e_data, w_data=w_data,
        x_data=x_data, prod=prod, threat=threat,
        # Achievements
        hints=hints, ach_summary=ach_summary, recent_achievements=recent_achievements,
        # Context
        is_new_user=is_new_user, greeting=greeting, name=name,
        login_streak=u.login_streak,
        # Goals
        weekly_task_goal=u.weekly_task_goal,
        weekly_habit_goal=u.weekly_habit_goal,
        # Referral
        referral_stats=get_referral_stats(u),
        # Legacy flat vars (ticker, HUD, charts)
        # total_xp is provided by **user_stats(u) — do not duplicate here
        overdue_tasks=t_data['overdue'],
        total_tasks=t_data['total'],
        completed_tasks=t_data['completed'],
        active_tasks=t_data['active'],
        completion_pct=t_data['completion_pct'],
        total_habits=h_data['total'],
        synced_today=h_data['synced_today'],
        weekly_labels=h_data['weekly_labels'],
        weekly_habits=h_data['weekly_syncs'],
        exp_labels=e_data['cat_labels'],
        exp_values=e_data['cat_values'],
        **user_stats(u), **shared_ctx(u),
    )
