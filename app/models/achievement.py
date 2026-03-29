"""
app/models/achievement.py — Achievement and UserAchievement models.

v10: Added 'tier' column (bronze / silver / gold) for visual hierarchy.
"""
from datetime import datetime, timezone
from app.extensions import db

TIER_COLORS = {
    'bronze': '#cd7f32',
    'silver': '#c0c0c0',
    'gold':   '#fbbf24',
}


class Achievement(db.Model):
    __tablename__ = 'achievements'

    id          = db.Column(db.Integer,    primary_key=True)
    key         = db.Column(db.String(40), unique=True, nullable=False)
    name        = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    icon        = db.Column(db.String(10), nullable=False, default='🏆')
    xp_reward   = db.Column(db.Integer,   nullable=False, default=50)
    tier        = db.Column(db.String(10), nullable=False, default='bronze')  # bronze silver gold

    unlocks = db.relationship('UserAchievement', back_populates='achievement',
                              lazy='dynamic')

    @property
    def tier_color(self) -> str:
        return TIER_COLORS.get(self.tier, '#64748b')

    def __repr__(self):
        return f'<Achievement {self.key!r} tier={self.tier}>'


class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                               nullable=False, index=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id', ondelete='CASCADE'),
                               nullable=False)
    unlocked_at    = db.Column(db.DateTime, nullable=False,
                               default=lambda: datetime.now(timezone.utc))

    user        = db.relationship('User',        back_populates='achievements')
    achievement = db.relationship('Achievement', back_populates='unlocks')

    def to_dict(self) -> dict:
        a = self.achievement
        return {
            'key':         a.key,
            'name':        a.name,
            'description': a.description,
            'icon':        a.icon,
            'xp_reward':   a.xp_reward,
            'tier':        a.tier,
            'tier_color':  a.tier_color,
            'unlocked_at': self.unlocked_at.isoformat(),
        }

    def __repr__(self):
        return f'<UserAchievement user={self.user_id} achievement={self.achievement_id}>'
