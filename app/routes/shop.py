"""app/routes/shop.py. Blueprint name: 'shop'. Endpoint: shop.shop, shop.buy_item."""
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.shop import ShopItem
from app.services.game_service import user_stats, shared_ctx
from app.services.shop_service import purchase_item
from . import Blueprint

shop_bp = Blueprint('shop', __name__)


@shop_bp.route('/shop', endpoint='shop')
@login_required
def shop():
    u         = current_user
    items     = ShopItem.query.order_by(ShopItem.sort_order).all()
    owned_ids = {inv.shop_item_id for inv in u.inventory}
    return render_template('shop.html',
        items=items, owned_ids=owned_ids,
        **user_stats(u), **shared_ctx(u),
    )


@shop_bp.route('/buy/<string:item>/<int:cost>', methods=['POST'], endpoint='buy_item')
@login_required
def buy_item(item, cost):
    success, msg = purchase_item(current_user, item)
    if success:
        flash(f'{item} acquired. Feature activated.', 'success')
    elif 'Insufficient' in msg:
        flash('Insufficient credits for that upgrade.', 'error')
    elif 'Already' in msg:
        flash(f'{item} is already installed.', 'info')
    else:
        flash(f'Purchase failed: {msg}', 'error')
    return redirect(url_for('shop.shop'))
