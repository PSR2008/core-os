"""
app/services/shop_service.py — Shop item seed data and purchase logic.

SHOP_ITEMS_SEED defines all purchasable items.
seed_shop_items() is called at app startup — safe to call repeatedly.
"""
from datetime import datetime, timedelta, timezone
from app.extensions import db

SHOP_ITEMS_SEED = [
    dict(name='Neural Booster',   feature_key='xp_boost',        cost=200,  item_type='passive',
         icon='🧠', sort_order=1,
         description='Permanent 2× XP multiplier on all task completions and habit syncs.'),
    dict(name='Task Amnesty',     feature_key='task_amnesty',    cost=250,  item_type='consumable',
         icon='🗑️', sort_order=2,
         description='One-time use: instantly purges all completed tasks from your archive.'),
    dict(name='Focus Shield',     feature_key='focus_mode',      cost=300,  item_type='timed',
         icon='🛡️', sort_order=3,
         description='2-hour focus countdown overlay — keeps you locked in across all pages.'),
    dict(name='Streak Guardian',  feature_key='streak_save',     cost=350,  item_type='passive',
         icon='⏳', sort_order=4,
         description='Protects habit streaks from resetting if you miss a single day.'),
    dict(name='Memory Crystal',   feature_key='cloud_backup',    cost=400,  item_type='passive',
         icon='💾', sort_order=5,
         description='One-click local JSON backup of all your stats, XP and progress data.'),
    dict(name='Credit Insurance', feature_key='credit_insurance', cost=500, item_type='consumable',
         icon='🔒', sort_order=6,
         description='Safety net: auto-tops balance to 300 CR when you drop below 100.'),
    dict(name='Cyberware Skin',   feature_key='theme_unlock',    cost=500,  item_type='skin',
         icon='🎨', sort_order=7,
         description='Unlocks the Crimson Protocol UI skin across all pages.'),
    dict(name='Habit Forge',      feature_key='habit_forge',     cost=650,  item_type='passive',
         icon='🔨', sort_order=8,
         description='Earn +15 CR bonus every time you sync a habit on a 7+ day streak.'),
    dict(name='Neon Matrix Skin', feature_key='neon_skin',       cost=750,  item_type='skin',
         icon='💚', sort_order=9,
         description='Unlocks the Neon Matrix UI skin — full-system green terminal aesthetic.'),
    dict(name='Void Skin',        feature_key='void_skin',       cost=800,  item_type='skin',
         icon='🌑', sort_order=10,
         description='Deep purple-black void aesthetic. Minimal, mysterious, powerful.'),
    dict(name='Solar Skin',       feature_key='solar_skin',      cost=800,  item_type='skin',
         icon='☀️', sort_order=11,
         description='Blazing amber and orange solar flare UI — raw power aesthetic.'),
    dict(name='XP Overdrive',     feature_key='xp_overdrive',    cost=1000, item_type='timed',
         icon='⚡', sort_order=12,
         description='Triple XP on all actions for 24 hours. Stacks above Neural Booster.'),
    dict(name='Database Relic',   feature_key='log_access',      cost=1200, item_type='passive',
         icon='📊', sort_order=13,
         description='Floating live panel shows XP, level, balance and threat on every page.'),
]


def seed_shop_items() -> None:
    """Insert any missing shop items. Safe to call on every startup."""
    from app.models.shop import ShopItem
    for item_data in SHOP_ITEMS_SEED:
        if not ShopItem.query.filter_by(feature_key=item_data['feature_key']).first():
            db.session.add(ShopItem(**item_data))
    db.session.commit()


def purchase_item(user, item_name: str):
    """
    Execute a shop purchase for `user`.
    Returns (True, message) on success, (False, error) on failure.
    """
    from app.models.shop import ShopItem, UserInventory

    item = ShopItem.query.filter_by(name=item_name).first()
    if not item:
        return False, 'Item not found.'

    # Prevent re-purchase
    already = UserInventory.query.filter_by(
        user_id=user.id, shop_item_id=item.id
    ).first()
    if already:
        return False, 'Already owned.'

    if user.balance < item.cost:
        return False, 'Insufficient credits.'

    user.balance -= item.cost
    inv = UserInventory(user_id=user.id, shop_item_id=item.id, is_active=True)
    db.session.add(inv)

    # ── Side effects ──────────────────────────────────────────────────────────
    if item.feature_key == 'task_amnesty':
        from app.models.task import Task
        Task.query.filter_by(user_id=user.id, completed=True).delete()
        inv.is_active = False   # consumed immediately

    elif item.feature_key == 'xp_overdrive':
        user.xp_overdrive_until = datetime.now(timezone.utc) + timedelta(hours=24)

    db.session.commit()
    return True, 'Purchase successful.'
