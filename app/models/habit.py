"""app/models/habit.py — Habit and HabitLog models with compound indexes."""
from datetime import datetime, date, timezone
from app.extensions import db


class Habit(db.Model):
    __tablename__ = 'habits'

    id             = db.Column(db.Integer,     primary_key=True)
    user_id        = db.Column(db.Integer,     db.ForeignKey('users.id', ondelete='CASCADE'),
                               nullable=False)
    name           = db.Column(db.String(100), nullable=False)
    streak         = db.Column(db.Integer,     nullable=False, default=0)
    last_completed = db.Column(db.Date,        nullable=True)
    created_at     = db.Column(db.DateTime,    nullable=False,
                               default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index('ix_habits_user_streak', 'user_id', 'streak'),
    )

    user = db.relationship('User',     back_populates='habits')
    logs = db.relationship('HabitLog', back_populates='habit',
                           lazy='dynamic', cascade='all, delete-orphan')

    def is_synced_today(self) -> bool:
        return self.last_completed == date.today()

    def to_dict(self) -> dict:
        return {
            'id':             self.id,
            'name':           self.name,
            'streak':         self.streak,
            'last_completed': self.last_completed.isoformat() if self.last_completed else None,
            'synced_today':   self.is_synced_today(),
        }

    def __repr__(self):
        return f'<Habit {self.name!r} streak={self.streak}>'


class HabitLog(db.Model):
    __tablename__ = 'habit_logs'

    id          = db.Column(db.Integer, primary_key=True)
    habit_id    = db.Column(db.Integer, db.ForeignKey('habits.id', ondelete='CASCADE'),
                            nullable=False)
    date_logged = db.Column(db.Date,    nullable=False, default=date.today)

    # Compound index: most queries are (habit_id, date_logged)
    # and range queries by date on joined habit_id + user_id
    __table_args__ = (
        db.Index('ix_habit_logs_habit_date', 'habit_id', 'date_logged'),
        db.UniqueConstraint('habit_id', 'date_logged', name='uq_habit_log_per_day'),
    )

    habit = db.relationship('Habit', back_populates='logs')

    def __repr__(self):
        return f'<HabitLog habit_id={self.habit_id} date={self.date_logged}>'
