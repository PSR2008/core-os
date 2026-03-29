"""
app/services/game_service.py — Core game mechanics.

Performance: shared_ctx now uses selectinload on inventory to avoid
N+1 queries (was: 1 list query + N shop_item lazy loads per page).
"""
from datetime import date, timedelta, datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app.extensions import db


def compute_threat_score(user, ctx=None) -> dict:
    """Aggregate threat score. Uses DataContext if provided (zero extra DB calls)."""
    if ctx is not None:
        overdue  = ctx.overdue_count()
        critical = ctx.critical_count()
        latest_w = ctx.recent_wellness(3)
    else:
        from app.models.task     import Task
        from app.models.wellness import WellnessLog
        today    = date.today()
        overdue  = Task.query.filter(
            Task.user_id == user.id, Task.completed == False,
            Task.due_date < today, Task.due_date.isnot(None),
        ).count()
        critical = Task.query.filter_by(user_id=user.id, completed=False, priority='CRITICAL').count()
        latest_w = WellnessLog.query.filter_by(user_id=user.id)\
            .order_by(WellnessLog.id.desc()).limit(3).all()

    budget_ratio = 0.0
    if user.budget > 0:
        budget_ratio = min(user.spent / user.budget, 1.5)

    score = (
        min(overdue  * 5, 40) +
        min(critical * 4, 20) +
        int(min(budget_ratio, 1.0) * 20)
    )
    if latest_w:
        avg_w  = sum((l.energy + l.clarity + l.mood) / 3 for l in latest_w) / len(latest_w)
        score += int(max(0, (5 - avg_w) / 5 * 20))
    score = min(score, 100)

    if   score >= 75: level, color, label = 'CRITICAL', '#f43f5e', 'CRITICAL_THREAT'
    elif score >= 50: level, color, label = 'HIGH',     '#fbbf24', 'ELEVATED_RISK'
    elif score >= 25: level, color, label = 'MODERATE', '#6366f1', 'NOMINAL_STRAIN'
    else:             level, color, label = 'LOW',      '#10b981', 'SYSTEM_STABLE'

    wellness_avg = (
        round(sum((l.energy + l.clarity + l.mood) / 3 for l in latest_w) / len(latest_w), 1)
        if latest_w else None
    )
    return dict(
        score=score, level=level, color=color, label=label,
        overdue=overdue, critical=critical,
        budget_pct=round(budget_ratio * 100),
        wellness_avg=wellness_avg,
    )


def apply_streak_decay(user, ctx=None) -> None:
    """Reset streaks for habits not synced yesterday or today."""
    if user.has_feature('streak_save'):
        return
    today     = date.today()
    yesterday = today - timedelta(days=1)
    habits    = ctx.habits if ctx else list(user.habits)
    changed   = False
    for habit in habits:
        lc = habit.last_completed
        if lc not in (today, yesterday) and habit.streak > 0:
            habit.streak = 0
            changed = True
    if changed:
        db.session.commit()


def award_xp(user, base_amount: int) -> int:
    earned = base_amount * user.get_xp_multiplier()
    user.total_xp += earned
    return earned


def award_credits(user, amount: int) -> None:
    user.balance += amount
    user.check_credit_insurance()


def user_stats(user) -> dict:
    user.check_credit_insurance()
    return dict(
        total_xp = user.total_xp,
        lvl      = user.level,
        lvl_pc   = user.level_progress,
        balance  = user.balance,
        budget   = user.budget,
        spent    = user.spent,
    )


def _load_inventory_eager(user):
    """
    Load user inventory with shop_item in a single JOIN query.
    Replaces lazy-load pattern that caused N+1 (one query per shop item).
    Returns a plain list — safe to iterate multiple times.
    """
    from app.models.shop import UserInventory
    return (
        UserInventory.query
        .options(selectinload(UserInventory.shop_item))
        .filter_by(user_id=user.id)
        .all()
    )


def shared_ctx(user) -> dict:
    """
    Skin state + inventory context injected into every template.
    Uses selectinload so inventory + shop_items are loaded in 2 queries,
    not 1 + N (was the case with lazy='dynamic' default load).
    """
    inventory   = _load_inventory_eager(user)
    owned_names = [inv.shop_item.name for inv in inventory if inv.shop_item]

    def _active(key):
        return any(
            inv.shop_item and inv.shop_item.feature_key == key and inv.is_active
            for inv in inventory
        )

    xp_until = None
    if _active('xp_overdrive') and user.xp_overdrive_until:
        xp_until = user.xp_overdrive_until.isoformat()

    return dict(
        crimson_active     = _active('theme_unlock'),
        neon_active        = _active('neon_skin'),
        void_active        = _active('void_skin'),
        solar_active       = _active('solar_skin'),
        owned_names        = owned_names,
        active_feat_names  = [
            inv.shop_item.name for inv in inventory
            if inv.shop_item and inv.is_active
        ],
        xp_overdrive_until = xp_until,
        operative_name     = user.operative_name or '',
        operative_age      = user.operative_age  or '',
        threat_score       = compute_threat_score(user)['score'],
    )
