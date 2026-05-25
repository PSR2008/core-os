import re

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db, limiter
from app.models.user import User

api_auth_bp = Blueprint('api_auth', __name__)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,32}$')


def _ok(data=None):
    return jsonify({'status': 'ok', 'data': data if data is not None else {}})


def _err(message, code=400):
    return jsonify({'status': 'error', 'error': message}), code


def _user_payload(user):
    user.ensure_referral_code()
    return {
        'id': user.id,
        'username': user.username,
        'operative_name': user.operative_name or user.username,
        'email': user.email,
        'level': user.level,
        'level_progress': user.level_progress,
        'total_xp': user.total_xp,
        'balance': user.balance,
        'login_streak': user.login_streak,
        'referral_code': user.referral_code or '',
        'onboarding_complete': user.onboarding_complete,
    }


@api_auth_bp.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit('20 per minute; 5 per 10 seconds')
def api_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))

    if not username or not password:
        return _err('username and password are required')

    user = User.query.filter(
        db.func.lower(User.username) == username.lower()
    ).first()

    if not user or not user.check_password(password):
        return _err('Invalid credentials.', 401)

    login_user(user, remember=True)
    user.update_login_streak()
    db.session.commit()

    return _ok(_user_payload(user))


@api_auth_bp.route('/api/v1/auth/register', methods=['POST'])
@limiter.limit('10 per minute')
def api_register():
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', ''))
    confirm = str(data.get('confirm', ''))

    errors = []
    if not _USERNAME_RE.match(username):
        errors.append('Username must be 3-32 chars, letters/numbers/underscores only.')
    if not _EMAIL_RE.match(email):
        errors.append('Enter a valid email address.')
    if len(password) < 8:
        errors.append('Password must be at least 8 characters.')
    if password != confirm:
        errors.append('Passwords do not match.')

    if errors:
        return _err('; '.join(errors))

    if User.query.filter(db.func.lower(User.username) == username.lower()).first():
        return _err('Username already taken.')
    if User.query.filter(db.func.lower(User.email) == email.lower()).first():
        return _err('Email already registered.')

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    user.ensure_referral_code()

    from app.services.growth_service import track
    track('register', user_id=user.id)

    login_user(user, remember=True)
    return _ok(_user_payload(user)), 201


@api_auth_bp.route('/api/v1/auth/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    session.clear()
    return _ok({'logged_out': True})


@api_auth_bp.route('/api/v1/auth/status', methods=['GET'])
def api_auth_status():
    if current_user.is_authenticated:
        return _ok({'authenticated': True, 'user': _user_payload(current_user)})
    return _ok({'authenticated': False, 'user': None})


@api_auth_bp.route('/api/v1/dashboard', methods=['GET'])
@login_required
def api_dashboard():
    import datetime as dt

    user = current_user
    user.update_login_streak()

    from app.services.analytics_service import (
        expense_analytics,
        habit_analytics,
        productivity_score,
        task_analytics,
        wellness_analytics,
    )
    from app.services.data_context import DataContext
    from app.services.game_service import compute_threat_score, user_stats
    from app.services.insights_service import generate_insights

    ctx = DataContext.build(user)
    task_data = task_analytics(ctx)
    habit_data = habit_analytics(ctx)
    expense_data = expense_analytics(ctx)
    wellness_data = wellness_analytics(ctx)
    productivity = productivity_score(ctx, task_data, habit_data, wellness_data)
    threat = compute_threat_score(user, ctx)
    stats = user_stats(user)
    insights = generate_insights(user, ctx)

    hour = dt.datetime.now().hour
    if hour < 12:
        greeting = 'Good morning'
    elif hour < 17:
        greeting = 'Good afternoon'
    elif hour < 21:
        greeting = 'Good evening'
    else:
        greeting = 'Late night session'

    return _ok({
        'greeting': greeting,
        'operative_name': user.operative_name or user.username,
        'user': {
            'level': user.level,
            'level_progress': user.level_progress,
            'total_xp': user.total_xp,
            'balance': user.balance,
            'login_streak': user.login_streak,
        },
        'threat': threat,
        'stats': stats,
        'productivity': productivity,
        'tasks': {
            'total': task_data.get('total', 0),
            'done': task_data.get('completed', 0),
            'active': task_data.get('active', 0),
            'overdue': task_data.get('overdue', 0),
            'critical': task_data.get('priority_counts', {}).get('CRITICAL', 0),
        },
        'habits': {
            'total': habit_data.get('total', 0),
            'synced_today': habit_data.get('synced_today', 0),
            'avg_streak': habit_data.get('combined_streak', 0),
        },
        'expenses': {
            'budget': user.budget,
            'spent': expense_data.get('this_month', 0),
            'remaining': expense_data.get('remaining', 0),
            'budget_pct': expense_data.get('budget_pct', 0),
        },
        'wellness': {
            'avg_mood': wellness_data.get('avg_mood'),
            'avg_energy': wellness_data.get('avg_energy'),
            'avg_clarity': wellness_data.get('avg_clarity'),
        },
        'insights': [str(item) for item in (insights or [])[:5]],
    })


@api_auth_bp.route('/api/v1/shop/items', methods=['GET'])
@login_required
def api_shop_items():
    from app.models.shop import ShopItem

    items = ShopItem.query.order_by(ShopItem.sort_order).all()
    owned_ids = [
        inv.shop_item_id
        for inv in current_user.inventory
        if inv.is_active
    ]
    return _ok({
        'items': [item.to_dict() for item in items],
        'owned_ids': owned_ids,
        'balance': current_user.balance,
    })


@api_auth_bp.route('/api/v1/shop/buy', methods=['POST'])
@login_required
@limiter.limit('30 per hour')
def api_shop_buy():
    from app.models.shop import ShopItem
    from app.services.shop_service import purchase_item

    data = request.get_json(silent=True) or {}
    feature_key = str(data.get('feature_key', '')).strip()
    if not feature_key:
        return _err('feature_key is required')

    item = ShopItem.query.filter_by(feature_key=feature_key).first()
    if not item:
        return _err('Item not found.', 404)

    success, message = purchase_item(current_user, item.name)
    if not success:
        return _err(message)

    return _ok({'purchased': True, 'message': message, 'balance': current_user.balance})
