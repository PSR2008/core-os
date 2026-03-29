"""
app/services/growth_service.py — Growth analytics and event tracking.

All writes use INSERT OR IGNORE semantics (via try/except on the unique
constraint) so routes can fire-and-forget without worrying about
duplicate events within a single day.
"""
from datetime import date, timedelta
from app.extensions import db


def track(event_type: str, user_id: int | None = None) -> None:
    """
    Record a growth event. Safe to call multiple times per day for
    the same (event_type, user_id) — duplicates are silently ignored.
    """
    from app.models.growth import GrowthEvent
    try:
        db.session.add(GrowthEvent(
            event_type=event_type,
            user_id=user_id,
            event_date=date.today(),
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()   # unique constraint violation — already tracked today


def dau_summary(days: int = 30) -> list[dict]:
    """
    Daily active users for the last `days` days.
    Returns list of {date, dau_count} dicts, oldest first.
    """
    from app.models.growth import GrowthEvent
    from sqlalchemy import func
    start = date.today() - timedelta(days=days)
    rows = (
        db.session.query(
            GrowthEvent.event_date,
            func.count(GrowthEvent.user_id.distinct()).label('cnt'),
        )
        .filter(
            GrowthEvent.event_type == 'dau',
            GrowthEvent.event_date >= start,
        )
        .group_by(GrowthEvent.event_date)
        .order_by(GrowthEvent.event_date)
        .all()
    )
    return [{'date': str(r.event_date), 'count': r.cnt} for r in rows]


def registration_summary(days: int = 30) -> list[dict]:
    """New registrations per day for the last `days` days."""
    from app.models.growth import GrowthEvent
    from sqlalchemy import func
    start = date.today() - timedelta(days=days)
    rows = (
        db.session.query(
            GrowthEvent.event_date,
            func.count(GrowthEvent.id).label('cnt'),
        )
        .filter(
            GrowthEvent.event_type == 'register',
            GrowthEvent.event_date >= start,
        )
        .group_by(GrowthEvent.event_date)
        .order_by(GrowthEvent.event_date)
        .all()
    )
    return [{'date': str(r.event_date), 'count': r.cnt} for r in rows]


def feature_usage_summary(days: int = 30) -> dict:
    """
    Total event counts per feature type over the last `days` days.
    Returns {event_type: count} for non-dau/register events.
    """
    from app.models.growth import GrowthEvent
    from sqlalchemy import func
    start = date.today() - timedelta(days=days)
    EXCLUDED = {'dau', 'register'}
    rows = (
        db.session.query(
            GrowthEvent.event_type,
            func.count(GrowthEvent.id).label('cnt'),
        )
        .filter(
            GrowthEvent.event_date >= start,
            GrowthEvent.event_type.notin_(EXCLUDED),
        )
        .group_by(GrowthEvent.event_type)
        .order_by(func.count(GrowthEvent.id).desc())
        .all()
    )
    return {r.event_type: r.cnt for r in rows}


def referral_count(days: int = 30) -> int:
    """Total successful referrals in the last `days` days."""
    from app.models.growth import GrowthEvent
    start = date.today() - timedelta(days=days)
    return GrowthEvent.query.filter(
        GrowthEvent.event_type == 'referral',
        GrowthEvent.event_date >= start,
    ).count()
