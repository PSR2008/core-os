"""app/models/task.py — Task model with compound indexes for hot query paths."""
from datetime import datetime, timezone
from app.extensions import db


class Task(db.Model):
    __tablename__ = 'tasks'

    id           = db.Column(db.Integer,     primary_key=True)
    user_id      = db.Column(db.Integer,     db.ForeignKey('users.id', ondelete='CASCADE'),
                             nullable=False)
    title        = db.Column(db.String(200), nullable=False)
    priority     = db.Column(db.String(10),  nullable=False, default='MED')
    status       = db.Column(db.String(12),  nullable=False, default='todo')
    due_date     = db.Column(db.Date,        nullable=True)
    due_time     = db.Column(db.String(5),   nullable=True)
    completed    = db.Column(db.Boolean,     nullable=False, default=False, index=True)
    completed_at = db.Column(db.DateTime,    nullable=True)
    created_at   = db.Column(db.DateTime,    nullable=False,
                             default=lambda: datetime.now(timezone.utc))

    # Compound indexes covering the hottest query patterns:
    #   filter_by(user_id=X, completed=True/False)  — most common
    #   filter(user_id=X, completed=False, due_date < today)  — overdue
    #   filter(user_id=X, completed=True, completed_at >= day)  — daily completions
    __table_args__ = (
        db.Index('ix_tasks_user_completed',    'user_id', 'completed'),
        db.Index('ix_tasks_user_priority',     'user_id', 'priority', 'completed'),
        db.Index('ix_tasks_user_completed_at', 'user_id', 'completed_at'),
        db.Index('ix_tasks_user_due_date',     'user_id', 'due_date'),
    )

    user = db.relationship('User', back_populates='tasks')

    PRIORITY_ORDER = {'CRITICAL': 1, 'HIGH': 2, 'MED': 3, 'LOW': 4}

    def complete(self) -> None:
        self.completed    = True
        self.status       = 'done'
        self.completed_at = datetime.now(timezone.utc)

    def reopen(self) -> None:
        self.completed    = False
        self.status       = 'todo'
        self.completed_at = None

    def set_inprogress(self) -> None:
        self.completed    = False
        self.status       = 'inprogress'
        self.completed_at = None

    def to_dict(self) -> dict:
        return {
            'id':           self.id,
            'title':        self.title,
            'priority':     self.priority,
            'status':       self.status,
            'due_date':     self.due_date.isoformat()     if self.due_date     else None,
            'due_time':     self.due_time,
            'completed':    self.completed,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at':   self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<Task {self.title[:40]!r} status={self.status}>'
