"""
app/services/referral_service.py — Referral system.

Referral flow:
  1. User shares their referral link:  /ref/<code>
  2. New visitor lands on /ref/<code>  → code stored in session
  3. New user registers               → referred_by_id set from session
  4. Reward both parties              → XP + achievement unlock

Rewards:
  Referrer:  +150 XP + 'referrer' achievement unlocked
  Referee:   +100 XP starter bonus
"""
from app.extensions import db


REFERRER_XP_REWARD = 150
REFEREE_XP_REWARD  = 100


def process_referral(new_user, referral_code: str) -> bool:
    """
    Called during registration if a referral code was in the session.
    Returns True if the referral was applied successfully.
    """
    from app.models.user import User
    from app.services.growth_service import track

    if not referral_code:
        return False

    referrer = User.query.filter_by(referral_code=referral_code.upper()).first()

    # Can't refer yourself, can't be referred twice
    if not referrer or referrer.id == new_user.id or new_user.referred_by_id:
        return False

    # Link referee to referrer
    new_user.referred_by_id = referrer.id

    # Award XP to both
    new_user.total_xp  += REFEREE_XP_REWARD
    referrer.total_xp  += REFERRER_XP_REWARD

    db.session.commit()

    # Track growth events
    track('referral', user_id=referrer.id)

    return True


def get_referral_stats(user) -> dict:
    """Return referral stats for a user's profile/dashboard."""
    from app.models.user import User

    # Count how many people used this user's code
    referred_count = User.query.filter_by(referred_by_id=user.id).count()

    return dict(
        referral_code=user.referral_code or '',
        referred_count=referred_count,
        xp_earned=referred_count * REFERRER_XP_REWARD,
    )
