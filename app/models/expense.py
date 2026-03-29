"""app/models/expense.py — Expense model with compound indexes."""
from datetime import datetime, date, timezone
from app.extensions import db


class Expense(db.Model):
    __tablename__ = 'expenses'

    id         = db.Column(db.Integer,    primary_key=True)
    user_id    = db.Column(db.Integer,    db.ForeignKey('users.id', ondelete='CASCADE'),
                           nullable=False)
    category   = db.Column(db.String(60), nullable=False)
    amount     = db.Column(db.Float,      nullable=False)
    note       = db.Column(db.String(200), nullable=True)
    date       = db.Column(db.Date,       nullable=False, default=date.today)
    created_at = db.Column(db.DateTime,   nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index('ix_expenses_user_date',     'user_id', 'date'),
        db.Index('ix_expenses_user_category', 'user_id', 'category'),
    )

    user = db.relationship('User', back_populates='expenses')

    def to_dict(self) -> dict:
        return {
            'id':       self.id,
            'category': self.category,
            'amount':   self.amount,
            'note':     self.note,
            'date':     self.date.isoformat(),
        }

    def __repr__(self):
        return f'<Expense {self.category} {self.amount}>'
