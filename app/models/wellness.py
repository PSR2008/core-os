"""app/models/wellness.py — WellnessLog model with compound index."""
from datetime import datetime, date, timezone
from app.extensions import db


class WellnessLog(db.Model):
    __tablename__ = 'wellness_logs'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                           nullable=False)
    energy     = db.Column(db.Integer, nullable=False)
    clarity    = db.Column(db.Integer, nullable=False)
    mood       = db.Column(db.Integer, nullable=False)
    notes      = db.Column(db.Text,    nullable=True)
    date       = db.Column(db.Date,    nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index('ix_wellness_user_date', 'user_id', 'date'),
        db.UniqueConstraint('user_id', 'date', name='uq_wellness_per_day'),
    )

    user = db.relationship('User', back_populates='wellness_logs')

    def to_dict(self) -> dict:
        return {
            'id':      self.id,
            'energy':  self.energy,
            'clarity': self.clarity,
            'mood':    self.mood,
            'notes':   self.notes,
            'date':    self.date.isoformat(),
        }

    def __repr__(self):
        return f'<WellnessLog {self.date} E{self.energy}/C{self.clarity}/M{self.mood}>'
