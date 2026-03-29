"""app/models/feedback.py — User-submitted feedback and bug reports."""
from datetime import datetime, timezone
from app.extensions import db


class UserFeedback(db.Model):
    __tablename__ = 'user_feedback'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'),
                           nullable=True, index=True)
    fb_type    = db.Column(db.String(20), nullable=False)   # 'bug' | 'feature' | 'general'
    message    = db.Column(db.Text, nullable=False)
    page       = db.Column(db.String(100), nullable=True)   # which page they were on
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<UserFeedback type={self.fb_type} user={self.user_id}>'
