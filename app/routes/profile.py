"""app/routes/profile.py — Operative Profile with identity, tiers, share link."""
from datetime import date
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.task    import Task
from app.models.habit   import HabitLog, Habit
from app.services.game_service import user_stats, shared_ctx, compute_threat_score
from app.services.identity_service   import get_operative_title, get_all_earned_titles
from app.services.achievement_service import get_achievement_summary
from . import Blueprint

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile', endpoint='profile')
@login_required
def profile():
    u         = current_user
    today     = date.today()
    today_str = today.strftime('%Y-%m-%d')

    habits      = Habit.query.filter_by(user_id=u.id).order_by(Habit.streak.desc()).all()
    tasks_done  = Task.query.filter_by(user_id=u.id, completed=True).count()
    tasks_open  = Task.query.filter_by(user_id=u.id, completed=False).count()
    done_today  = Task.query.filter(
        Task.user_id == u.id, Task.completed == True, Task.completed_at >= today,
    ).count()
    synced_today        = sum(1 for h in habits if h.is_synced_today())
    owned_items         = list(u.inventory.all())
    recent_tasks        = Task.query.filter_by(user_id=u.id).order_by(Task.id.desc()).limit(8).all()
    threat              = compute_threat_score(u)
    total_habits_synced = HabitLog.query.join(HabitLog.habit).filter(Habit.user_id == u.id).count()

    # Identity & achievements
    identity      = get_operative_title(u)
    earned_titles = get_all_earned_titles(u)
    ach_summary   = get_achievement_summary(u)
    all_ach       = u.achievements.order_by(
        __import__('app.models.achievement', fromlist=['UserAchievement']).UserAchievement.unlocked_at.desc()
    ).all()

    return render_template('profile.html',
        habits=habits, top_habits=habits[:5],
        tasks_done=tasks_done, tasks_open=tasks_open,
        done_today=done_today, synced_today=synced_today,
        owned_items=owned_items, recent_tasks=recent_tasks,
        threat=threat, total_habits_synced=total_habits_synced,
        today_str=today_str,
        identity=identity, earned_titles=earned_titles,
        ach_summary=ach_summary, all_ach=all_ach,
        **user_stats(u), **shared_ctx(u),
    )


@profile_bp.route('/set_profile', methods=['POST'], endpoint='set_profile')
@login_required
def set_profile():
    u    = current_user
    name = request.form.get('name', '').strip()
    if not name:
        flash('Operative name cannot be empty.', 'error')
        return redirect(url_for('profile.profile'))
    if len(name) > 60:
        flash('Name too long (max 60 characters).', 'error')
        return redirect(url_for('profile.profile'))
    try:
        age = int(request.form.get('age', '0'))
        age = age if 0 < age <= 120 else None
    except (ValueError, TypeError):
        age = None

    u.operative_name = name
    u.operative_age  = age
    db.session.commit()
    flash(f'Operative profile updated — {name}.', 'success')
    return redirect(url_for('dashboard.index'))


@profile_bp.route('/set_goals', methods=['POST'], endpoint='set_goals')
@login_required
def set_goals():
    """Update weekly task and habit goals."""
    u = current_user
    try:
        task_goal  = int(request.form.get('weekly_task_goal',  u.weekly_task_goal))
        habit_goal = int(request.form.get('weekly_habit_goal', u.weekly_habit_goal))
        if 1 <= task_goal <= 50:
            u.weekly_task_goal = task_goal
        if 1 <= habit_goal <= 70:
            u.weekly_habit_goal = habit_goal
        db.session.commit()
        flash(f'Weekly goals updated: {task_goal} tasks / {habit_goal} habit syncs.', 'success')
    except ValueError:
        flash('Invalid goal values.', 'error')
    return redirect(url_for('profile.profile'))
