"""
app/routes/habits.py — Habit Sync.

Performance fix: heatmap was N×30 queries (one per habit per day).
Now: single bulk query for all logs, built into dicts in Python.
"""
from datetime import date, timedelta
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.habit import Habit, HabitLog
from app.services.game_service import user_stats, shared_ctx, award_xp, award_credits, apply_streak_decay
from app.services.achievement_service import check_and_unlock
from app.services.growth_service import track
from . import Blueprint

habits_bp = Blueprint('habits', __name__)
HABIT_LIMIT = 50   # max habits rendered per page


@habits_bp.route('/habits', methods=['GET', 'POST'], endpoint='habits')
@login_required
def habits():
    u = current_user
    if request.method == 'POST':
        name = request.form.get('habit', '').strip()
        if not name:
            flash('Habit name cannot be empty.', 'error')
        elif len(name) > 100:
            flash('Habit name too long (max 100 chars).', 'error')
        else:
            db.session.add(Habit(user_id=u.id, name=name))
            db.session.commit()
            track('habit_create', user_id=u.id)
            flash(f'Habit "{name}" initialized.', 'success')
        return redirect(url_for('habits.habits'))

    apply_streak_decay(u)

    # Paginate habits — rare that anyone has 50+, but safe
    habit_list = (Habit.query.filter_by(user_id=u.id)
                  .order_by(Habit.streak.desc(), Habit.id)
                  .limit(HABIT_LIMIT).all())

    today_dt = date.today()
    today    = today_dt.strftime('%Y-%m-%d')

    # ── Heatmap: ONE query for all habits × 30 days ──────────────────────────
    # Old: N habits × 30 days = N×30 individual queries
    # New: 1 query → build lookup dict → O(1) per cell
    if habit_list:
        habit_ids    = [h.id for h in habit_list]
        cutoff       = today_dt - timedelta(days=29)
        recent_logs  = HabitLog.query.filter(
            HabitLog.habit_id.in_(habit_ids),
            HabitLog.date_logged >= cutoff,
        ).all()

        # Build a set of (habit_id, date) tuples for O(1) lookup
        synced_set = {(log.habit_id, log.date_logged) for log in recent_logs}
    else:
        synced_set = set()

    heatmap_data = {}
    for h in habit_list:
        heatmap_data[h.id] = [
            {
                'date': (today_dt - timedelta(days=i)).strftime('%Y-%m-%d'),
                'done': (h.id, today_dt - timedelta(days=i)) in synced_set,
            }
            for i in range(29, -1, -1)
        ]

    return render_template('habits.html',
        habits=habit_list, today=today, heatmap_data=heatmap_data,
        habit_limit=HABIT_LIMIT, habit_count=Habit.query.filter_by(user_id=u.id).count(),
        **user_stats(u), **shared_ctx(u),
    )


@habits_bp.route('/sync_habit/<int:id>', methods=['POST'], endpoint='sync_habit')
@login_required
def sync_habit(id):
    u     = current_user
    habit = Habit.query.filter_by(id=id, user_id=u.id).first_or_404()
    today     = date.today()
    yesterday = today - timedelta(days=1)

    if habit.last_completed == today:
        flash(f'"{habit.name}" already synced today.', 'info')
        return redirect(url_for('habits.habits'))

    last = habit.last_completed
    if last == yesterday:
        new_streak = habit.streak + 1
    elif last is None:
        new_streak = 1
    else:
        protected  = u.has_feature('streak_save') and last >= (today - timedelta(days=2))
        new_streak = (habit.streak + 1) if protected else 1

    habit.streak         = new_streak
    habit.last_completed = today

    # Guard against race-condition duplicate insert (UniqueConstraint fallback)
    existing_log = HabitLog.query.filter_by(habit_id=habit.id, date_logged=today).first()
    if not existing_log:
        try:
            db.session.add(HabitLog(habit_id=habit.id, date_logged=today))
            db.session.flush()  # catch IntegrityError before commit
        except IntegrityError:
            db.session.rollback()  # already logged today — safe to continue

    cr_gain = 20
    if u.has_feature('habit_forge') and new_streak >= 7:
        cr_gain += 15

    earned = award_xp(u, 5)
    award_credits(u, cr_gain)
    db.session.commit()
    check_and_unlock(u)
    track('habit_sync', user_id=u.id)
    flash(f'"{habit.name}" synced — streak {new_streak}d  +{earned} XP  +{cr_gain} CR.', 'success')
    return redirect(url_for('habits.habits'))


@habits_bp.route('/delete/habits/<int:id>', methods=['POST'], endpoint='delete_habit')
@login_required
def delete_habit(id):
    habit = Habit.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name  = habit.name
    db.session.delete(habit)
    db.session.commit()
    flash(f'Habit "{name}" terminated.', 'info')
    return redirect(request.referrer or url_for('habits.habits'))
