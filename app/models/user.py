"""
app/models/user.py

v11 additions:
  referral_code    — unique 8-char code generated at registration
  referred_by_id   — FK to the user who referred this user (nullable)
  onboarding_step  — 0 = complete, 1-3 = which step user is on
"""
from datetime import datetime, date, timezone, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(32),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # ── Game state ─────────────────────────────────────────────────────────────
    total_xp           = db.Column(db.Integer,  nullable=False, default=0)
    balance            = db.Column(db.Integer,  nullable=False, default=1000)
    budget             = db.Column(db.Float,    nullable=False, default=50000.0)
    operative_name     = db.Column(db.String(60), nullable=True)
    operative_age      = db.Column(db.Integer,   nullable=True)
    active_skin        = db.Column(db.String(32), nullable=False, default='default')
    xp_overdrive_until = db.Column(db.DateTime,  nullable=True)

    # ── Retention ─────────────────────────────────────────────────────────────
    login_streak    = db.Column(db.Integer, nullable=False, default=0)
    last_login_date = db.Column(db.Date,    nullable=True)

    # ── Premium & goals ───────────────────────────────────────────────────────
    is_premium        = db.Column(db.Boolean, nullable=False, default=False)
    weekly_task_goal  = db.Column(db.Integer, nullable=False, default=5)
    weekly_habit_goal = db.Column(db.Integer, nullable=False, default=7)

    # ── Growth (v11) ──────────────────────────────────────────────────────────
    referral_code   = db.Column(db.String(12), unique=True, nullable=True, index=True)
    referred_by_id  = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'),
                                nullable=True)
    onboarding_step = db.Column(db.Integer, nullable=False, default=1)
    # 0 = onboarding complete
    # 1 = step 1: name your operative
    # 2 = step 2: add first task
    # 3 = step 3: add first habit

    # ── Relationships ──────────────────────────────────────────────────────────
    tasks         = db.relationship('Task',            back_populates='user',
                                    lazy='dynamic',    cascade='all, delete-orphan')
    habits        = db.relationship('Habit',           back_populates='user',
                                    lazy='dynamic',    cascade='all, delete-orphan')
    expenses      = db.relationship('Expense',         back_populates='user',
                                    lazy='dynamic',    cascade='all, delete-orphan')
    wellness_logs = db.relationship('WellnessLog',     back_populates='user',
                                    lazy='dynamic',    cascade='all, delete-orphan')
    inventory     = db.relationship('UserInventory',   back_populates='user',
                                    lazy='dynamic',    cascade='all, delete-orphan')
    achievements  = db.relationship('UserAchievement', back_populates='user',
                                    lazy='dynamic',    cascade='all, delete-orphan')
    referrals     = db.relationship('User', foreign_keys=[referred_by_id],
                                    primaryjoin='User.referred_by_id == User.id',
                                    backref=db.backref('referrer', remote_side='User.id'),
                                    lazy='dynamic')

    # ── Auth ───────────────────────────────────────────────────────────────────
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # ── Referral code ──────────────────────────────────────────────────────────
    def ensure_referral_code(self) -> str:
        if not self.referral_code:
            import secrets, string
            alphabet  = string.ascii_uppercase + string.digits
            max_tries = 20  # 36^8 ≈ 2.8 trillion combinations — limit is purely defensive
            for _ in range(max_tries):
                code = ''.join(secrets.choice(alphabet) for _ in range(8))
                if not User.query.filter_by(referral_code=code).first():
                    self.referral_code = code
                    db.session.commit()
                    break
        return self.referral_code or ''

    # ── Onboarding ─────────────────────────────────────────────────────────────
    @property
    def onboarding_complete(self) -> bool:
        return self.onboarding_step == 0

    # ── Level ──────────────────────────────────────────────────────────────────
    @property
    def level(self) -> int:
        return (self.total_xp // 100) + 1

    @property
    def level_progress(self) -> int:
        return self.total_xp % 100

    # ── Login streak ───────────────────────────────────────────────────────────
    def update_login_streak(self) -> int:
        today     = date.today()
        yesterday = today - timedelta(days=1)
        if self.last_login_date == today:
            return self.login_streak
        self.login_streak = (self.login_streak + 1) if self.last_login_date == yesterday else 1
        self.last_login_date = today
        db.session.commit()
        return self.login_streak

    # ── Inventory ──────────────────────────────────────────────────────────────
    @property
    def owned_feature_keys(self) -> set:
        return {inv.shop_item.feature_key
                for inv in self.inventory
                if inv.shop_item and inv.is_active}

    def has_feature(self, key: str) -> bool:
        return key in self.owned_feature_keys

    # ── Economy ────────────────────────────────────────────────────────────────
    @property
    def spent(self) -> float:
        from sqlalchemy import func
        result = db.session.query(func.sum(Expense.amount))\
            .filter(Expense.user_id == self.id).scalar()
        return float(result or 0)

    def get_xp_multiplier(self) -> int:
        now = datetime.now(timezone.utc)
        inv = self.inventory.join(ShopItem)\
            .filter(ShopItem.feature_key == 'xp_overdrive',
                    UserInventory.is_active == True).first()
        if inv and self.xp_overdrive_until:
            expiry = self.xp_overdrive_until
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if now < expiry:
                return 3
            inv.is_active = False
            db.session.commit()
        if self.has_feature('xp_boost'):
            return 2
        return 1

    def check_credit_insurance(self) -> None:
        if self.balance >= 100:
            return
        inv = self.inventory.join(ShopItem)\
            .filter(ShopItem.feature_key == 'credit_insurance',
                    UserInventory.is_active == True).first()
        if inv:
            self.balance  = 300
            inv.is_active = False
            db.session.commit()

    def __repr__(self):
        return f'<User {self.username!r} lvl={self.level}>'


from app.models.expense  import Expense                  # noqa: E402
from app.models.shop     import ShopItem, UserInventory  # noqa: E402
