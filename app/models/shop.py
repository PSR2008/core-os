"""
app/models/shop.py — ShopItem and UserInventory models.

ShopItem rows are seeded once at startup (see services/shop_service.py).
UserInventory records each purchase per user. is_active lets us
deactivate timed or consumable features without deleting the purchase record.
"""
from datetime import datetime, timezone
from app.extensions import db


class ShopItem(db.Model):
    __tablename__ = 'shop_items'

    id          = db.Column(db.Integer,    primary_key=True)
    name        = db.Column(db.String(60), unique=True, nullable=False)
    feature_key = db.Column(db.String(40), unique=True, nullable=False)
    cost        = db.Column(db.Integer,    nullable=False)
    item_type   = db.Column(db.String(20), nullable=False)   # passive timed consumable skin
    icon        = db.Column(db.String(10), nullable=False, default='📦')
    description = db.Column(db.String(200), nullable=True)
    sort_order  = db.Column(db.Integer,    nullable=False, default=0)

    purchases = db.relationship('UserInventory', back_populates='shop_item',
                                lazy='dynamic')

    def to_dict(self) -> dict:
        return {
            'id':          self.id,
            'name':        self.name,
            'feature_key': self.feature_key,
            'cost':        self.cost,
            'item_type':   self.item_type,
            'icon':        self.icon,
            'description': self.description,
        }

    def __repr__(self):
        return f'<ShopItem {self.name!r} {self.cost}CR>'


class UserInventory(db.Model):
    __tablename__ = 'user_inventory'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                             nullable=False, index=True)
    shop_item_id = db.Column(db.Integer, db.ForeignKey('shop_items.id', ondelete='CASCADE'),
                             nullable=False)
    is_active    = db.Column(db.Boolean, nullable=False, default=True)
    purchased_at = db.Column(db.DateTime, nullable=False,
                             default=lambda: datetime.now(timezone.utc))

    user      = db.relationship('User',     back_populates='inventory')
    shop_item = db.relationship('ShopItem', back_populates='purchases')

    def to_dict(self) -> dict:
        return {
            'item':         self.shop_item.to_dict() if self.shop_item else {},
            'is_active':    self.is_active,
            'purchased_at': self.purchased_at.isoformat(),
        }

    def __repr__(self):
        name = self.shop_item.name if self.shop_item else '?'
        return f'<UserInventory user={self.user_id} item={name!r} active={self.is_active}>'
