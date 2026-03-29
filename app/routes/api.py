"""
app/routes/api.py — REST JSON API, mobile-ready.

Standards:
  - All responses: { status, data } or { status, error }
  - All list endpoints: paginated with { items, page, pages, total }
  - Auth: session cookie (same as web) — token auth can be added later
  - Errors: consistent error codes and messages
  - Rate limiting: inherits Flask-Limiter app defaults
  - PUT endpoints for updates (completes mobile CRUD)
"""
from datetime import date, datetime
from flask import jsonify, request
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models.task     import Task
from app.models.habit    import Habit, HabitLog
from app.models.expense  import Expense
from app.models.wellness import WellnessLog
from app.services.game_service import user_stats, compute_threat_score
from . import Blueprint

api_bp = Blueprint('api', __name__)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE     = 100


# ── Response helpers ──────────────────────────────────────────────────────────

def _ok(data=None, **kw):
    return jsonify({'status': 'ok', 'data': data if data is not None else {}, **kw})

def _list_ok(items, page, pages, total):
    return jsonify({'status': 'ok',
                    'data': {'items': items, 'page': page, 'pages': pages, 'total': total}})

def _err(msg, code=400):
    return jsonify({'status': 'error', 'error': msg}), code

def _parse_page():
    try:
        size = min(int(request.args.get('per_page', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
        page = max(int(request.args.get('page', 1)), 1)
        return page, size
    except ValueError:
        return 1, DEFAULT_PAGE_SIZE

def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None


# ── Stats ─────────────────────────────────────────────────────────────────────

@limiter.limit('300 per hour; 60 per minute')
@api_bp.route('/api/stats', endpoint='api_stats')
@login_required
def api_stats():
    u      = current_user
    stats  = user_stats(u)
    threat = compute_threat_score(u)
    return jsonify({**stats,
        'threat_score':  threat['score'],
        'threat_label':  threat['label'],
        'threat_level':  threat['level'],
        'login_streak':  u.login_streak,
        'referral_code': u.referral_code or '',
    })


# ── Tasks ─────────────────────────────────────────────────────────────────────

@limiter.limit('300 per hour; 60 per minute')
@api_bp.route('/api/v1/tasks', methods=['GET'])
@login_required
def api_tasks_list():
    uid     = current_user.id
    page, size = _parse_page()
    status  = request.args.get('status')   # 'active' | 'done' | None = all
    priority = request.args.get('priority')

    q = Task.query.filter_by(user_id=uid)
    if status == 'active':  q = q.filter_by(completed=False)
    elif status == 'done':  q = q.filter_by(completed=True)
    if priority and priority in ('CRITICAL','HIGH','MED','LOW'):
        q = q.filter_by(priority=priority)

    total  = q.count()
    pages  = max((total + size - 1) // size, 1)
    tasks  = q.order_by(Task.id.desc()).limit(size).offset((page-1)*size).all()
    return _list_ok([t.to_dict() for t in tasks], page, pages, total)


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/tasks', methods=['POST'])
@login_required
def api_tasks_create():
    data     = request.get_json(silent=True) or {}
    title    = str(data.get('title', '')).strip()
    priority = str(data.get('priority', 'MED')).upper()
    if not title:                                    return _err('title is required')
    if priority not in ('CRITICAL','HIGH','MED','LOW'): priority = 'MED'
    due_date = _parse_date(data.get('due_date'))
    t = Task(user_id=current_user.id, title=title, priority=priority,
             due_date=due_date, due_time=data.get('due_time'))
    db.session.add(t); db.session.commit()
    return _ok(t.to_dict()), 201


@limiter.limit('300 per hour; 60 per minute')
@api_bp.route('/api/v1/tasks/<int:id>', methods=['GET'])
@login_required
def api_tasks_get(id):
    t = Task.query.filter_by(id=id, user_id=current_user.id).first()
    if not t: return _err('not found', 404)
    return _ok(t.to_dict())


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/tasks/<int:id>', methods=['PUT', 'PATCH'])
@login_required
def api_tasks_update(id):
    t = Task.query.filter_by(id=id, user_id=current_user.id).first()
    if not t: return _err('not found', 404)
    data = request.get_json(silent=True) or {}

    if 'title' in data:
        title = str(data['title']).strip()
        if not title: return _err('title cannot be empty')
        t.title = title[:200]

    if 'priority' in data:
        p = str(data['priority']).upper()
        if p in ('CRITICAL','HIGH','MED','LOW'): t.priority = p

    if 'status' in data:
        s = str(data['status'])
        if s == 'done' and not t.completed:
            from app.services.game_service import award_xp, award_credits
            t.complete()
            award_xp(current_user, 10)
            award_credits(current_user, 50)
        elif s == 'inprogress': t.set_inprogress()
        elif s == 'todo':       t.reopen()

    if 'due_date' in data:
        t.due_date = _parse_date(data['due_date'])

    db.session.commit()
    return _ok(t.to_dict())


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/tasks/<int:id>', methods=['DELETE'])
@login_required
def api_tasks_delete(id):
    t = Task.query.filter_by(id=id, user_id=current_user.id).first()
    if not t: return _err('not found', 404)
    db.session.delete(t); db.session.commit()
    return _ok()


# ── Habits ────────────────────────────────────────────────────────────────────

@limiter.limit('300 per hour; 60 per minute')
@api_bp.route('/api/v1/habits', methods=['GET'])
@login_required
def api_habits_list():
    uid       = current_user.id
    page, size = _parse_page()
    total  = Habit.query.filter_by(user_id=uid).count()
    pages  = max((total + size - 1) // size, 1)
    habits = (Habit.query.filter_by(user_id=uid)
              .order_by(Habit.streak.desc())
              .limit(size).offset((page-1)*size).all())
    return _list_ok([h.to_dict() for h in habits], page, pages, total)


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/habits', methods=['POST'])
@login_required
def api_habits_create():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    if not name: return _err('name is required')
    if len(name) > 100: return _err('name too long (max 100 chars)')
    h = Habit(user_id=current_user.id, name=name)
    db.session.add(h); db.session.commit()
    return _ok(h.to_dict()), 201


@limiter.limit('300 per hour; 60 per minute')
@api_bp.route('/api/v1/habits/<int:id>', methods=['GET'])
@login_required
def api_habits_get(id):
    h = Habit.query.filter_by(id=id, user_id=current_user.id).first()
    if not h: return _err('not found', 404)
    return _ok(h.to_dict())


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/habits/<int:id>/sync', methods=['POST'])
@login_required
def api_habits_sync(id):
    """Sync a habit for today — equivalent to pressing SYNC_NEURAL_LINK."""
    u     = current_user
    habit = Habit.query.filter_by(id=id, user_id=u.id).first()
    if not habit: return _err('not found', 404)

    today     = date.today()
    from datetime import timedelta
    yesterday = today - timedelta(days=1)

    if habit.last_completed == today:
        return _ok({'synced': False, 'reason': 'already synced today',
                    'streak': habit.streak})

    last = habit.last_completed
    new_streak = (habit.streak + 1) if last in (yesterday, None) or \
                 (u.has_feature('streak_save') and last and last >= today - timedelta(days=2)) \
                 else 1
    if last is None: new_streak = 1

    habit.streak         = new_streak
    habit.last_completed = today
    existing = HabitLog.query.filter_by(habit_id=habit.id, date_logged=today).first()
    if not existing:
        db.session.add(HabitLog(habit_id=habit.id, date_logged=today))

    from app.services.game_service import award_xp, award_credits
    earned  = award_xp(u, 5)
    cr_gain = 20 + (15 if u.has_feature('habit_forge') and new_streak >= 7 else 0)
    award_credits(u, cr_gain)
    db.session.commit()
    return _ok({'synced': True, 'streak': new_streak, 'xp_earned': earned, 'cr_earned': cr_gain})


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/habits/<int:id>', methods=['DELETE'])
@login_required
def api_habits_delete(id):
    h = Habit.query.filter_by(id=id, user_id=current_user.id).first()
    if not h: return _err('not found', 404)
    db.session.delete(h); db.session.commit()
    return _ok()


# ── Expenses ──────────────────────────────────────────────────────────────────

@limiter.limit('300 per hour; 60 per minute')
@api_bp.route('/api/v1/expenses', methods=['GET'])
@login_required
def api_expenses_list():
    uid       = current_user.id
    page, size = _parse_page()
    total  = Expense.query.filter_by(user_id=uid).count()
    pages  = max((total + size - 1) // size, 1)
    exps   = (Expense.query.filter_by(user_id=uid)
              .order_by(Expense.id.desc())
              .limit(size).offset((page-1)*size).all())
    return _list_ok([e.to_dict() for e in exps], page, pages, total)


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/expenses', methods=['POST'])
@login_required
def api_expenses_create():
    data = request.get_json(silent=True) or {}
    category = str(data.get('category', '')).strip()
    try:    amount = float(data.get('amount', 0))
    except: return _err('amount must be a number')
    if not category:    return _err('category is required')
    if amount <= 0:     return _err('amount must be positive')
    if amount > 1e7:    return _err('amount exceeds maximum')
    e = Expense(user_id=current_user.id, category=category,
                amount=round(amount, 2), date=date.today())
    db.session.add(e); db.session.commit()
    return _ok(e.to_dict()), 201


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/expenses/<int:id>', methods=['DELETE'])
@login_required
def api_expenses_delete(id):
    e = Expense.query.filter_by(id=id, user_id=current_user.id).first()
    if not e: return _err('not found', 404)
    db.session.delete(e); db.session.commit()
    return _ok()


# ── Wellness ──────────────────────────────────────────────────────────────────

@limiter.limit('300 per hour; 60 per minute')
@api_bp.route('/api/v1/wellness', methods=['GET'])
@login_required
def api_wellness_list():
    uid       = current_user.id
    page, size = _parse_page()
    total  = WellnessLog.query.filter_by(user_id=uid).count()
    pages  = max((total + size - 1) // size, 1)
    logs   = (WellnessLog.query.filter_by(user_id=uid)
              .order_by(WellnessLog.id.desc())
              .limit(size).offset((page-1)*size).all())
    return _list_ok([l.to_dict() for l in logs], page, pages, total)


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/wellness', methods=['POST'])
@login_required
def api_wellness_create():
    data = request.get_json(silent=True) or {}
    try:
        energy  = int(data.get('energy',  5))
        clarity = int(data.get('clarity', 5))
        mood    = int(data.get('mood',    5))
    except:
        return _err('energy, clarity, mood must be integers 1–10')
    if not all(1 <= v <= 10 for v in [energy, clarity, mood]):
        return _err('all values must be between 1 and 10')
    l = WellnessLog(user_id=current_user.id, date=date.today(),
                    energy=energy, clarity=clarity, mood=mood,
                    notes=str(data.get('notes', '')).strip() or None)
    db.session.add(l); db.session.commit()
    return _ok(l.to_dict()), 201


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/wellness/<int:id>', methods=['DELETE'])
@login_required
def api_wellness_delete(id):
    l = WellnessLog.query.filter_by(id=id, user_id=current_user.id).first()
    if not l: return _err('not found', 404)
    db.session.delete(l); db.session.commit()
    return _ok()


# ── User profile (mobile app convenience) ─────────────────────────────────────

@limiter.limit('300 per hour; 60 per minute')
@api_bp.route('/api/v1/me', methods=['GET'])
@login_required
def api_me():
    u = current_user
    return _ok({
        'id':             u.id,
        'username':       u.username,
        'operative_name': u.operative_name,
        'level':          u.level,
        'level_progress': u.level_progress,
        'total_xp':       u.total_xp,
        'balance':        u.balance,
        'login_streak':   u.login_streak,
        'referral_code':  u.referral_code or '',
        'created_at':     u.created_at.isoformat(),
    })


@limiter.limit('120 per hour; 20 per minute')
@api_bp.route('/api/v1/me', methods=['PATCH'])
@login_required
def api_me_update():
    u    = current_user
    data = request.get_json(silent=True) or {}
    if 'operative_name' in data:
        name = str(data['operative_name']).strip()[:60]
        if name: u.operative_name = name
    if 'operative_age' in data:
        try:
            age = int(data['operative_age'])
            if 0 < age <= 120: u.operative_age = age
        except (ValueError, TypeError):
            pass
    if 'budget' in data:
        try:
            b = float(data['budget'])
            if b >= 0: u.budget = round(b, 2)
        except (ValueError, TypeError):
            pass
    db.session.commit()
    return _ok({'updated': True})
