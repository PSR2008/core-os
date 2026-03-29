"""
app/models/growth.py — Lightweight admin-facing growth analytics.

Tracks coarse events: registrations, daily_active, feature_use.
One row per (event_type, date, user_id) — safe to insert duplicates
via upsert logic. No PII stored beyond user_id.

event_type values:
  'register'    — new user created
  'dau'         — user visited dashboard on this date
  'task_create' — task added
  'task_done'   — task completed
  'habit_sync'  — habit synced
  'expense_log' — expense logged
  'wellness_log'— wellness logged
  'referral'    — referral converted
"""
from datetime import datetime, date, timezone
from app.extensions import db


class GrowthEvent(db.Model):
    __tablename__ = 'growth_events'

    id         = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(30), nullable=False, index=True)
    user_id    = db.Column(db.Integer, nullable=True, index=True)  # nullable for aggregate events
    event_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('event_type', 'user_id', 'event_date',
                            name='uq_growth_event_per_user_day'),
    )

    def __repr__(self):
        return f'<GrowthEvent {self.event_type} user={self.user_id} {self.event_date}>'
