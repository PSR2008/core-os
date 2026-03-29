"""app/routes/tasks.py — Task Matrix with pagination."""
from datetime import date, datetime
from flask import render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.task import Task
from app.services.game_service import user_stats, shared_ctx, award_xp, award_credits
from app.services.achievement_service import check_and_unlock
from app.services.growth_service import track
from . import Blueprint

tasks_bp = Blueprint('tasks', __name__)

_PRIORITY_CASE = (
    "CASE priority WHEN 'CRITICAL' THEN 1 "
    "WHEN 'HIGH' THEN 2 WHEN 'MED' THEN 3 ELSE 4 END"
)
ACTIVE_PAGE_SIZE = 50   # max active tasks shown per page
DONE_PAGE_SIZE   = 20   # completed tasks per page


@tasks_bp.route('/tasks', methods=['GET', 'POST'], endpoint='tasks')
@login_required
def tasks():
    u        = current_user
    confetti = request.args.get('confetti', '0')

    if request.method == 'POST':
        title        = request.form.get('task', '').strip()
        priority     = request.form.get('priority', 'MED')
        due_date_str = request.form.get('due_date', '').strip()
        due_time     = request.form.get('due_time', '').strip()

        if not title:
            flash('Task title cannot be empty.', 'error')
            return redirect(url_for('tasks.tasks'))
        if len(title) > 200:
            flash('Task title too long (max 200 characters).', 'error')
            return redirect(url_for('tasks.tasks'))
        if priority not in ('CRITICAL', 'HIGH', 'MED', 'LOW'):
            priority = 'MED'

        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'error')
                return redirect(url_for('tasks.tasks'))

        db.session.add(Task(
            user_id=u.id, title=title[:200], priority=priority,
            due_date=due_date, due_time=(due_time[:10] if due_time else None),
        ))
        db.session.commit()
        track('task_create', user_id=u.id)
        flash(f'Task "{title}" added to matrix.', 'success')
        return redirect(url_for('tasks.tasks'))

    filter_p  = request.args.get('filter', 'ALL')
    if filter_p not in ('ALL', 'CRITICAL', 'HIGH', 'MED', 'LOW'):
        filter_p = 'ALL'
    try:
        page = max(int(request.args.get('page', 1)), 1)
    except (ValueError, TypeError):
        page = 1
    today_str = date.today().strftime('%Y-%m-%d')

    # Active tasks — paginated, priority-ordered
    q = Task.query.filter_by(user_id=u.id, completed=False)
    if filter_p != 'ALL':
        q = q.filter_by(priority=filter_p)
    active_q = q.order_by(db.text(_PRIORITY_CASE), Task.id.desc())
    active   = active_q.limit(ACTIVE_PAGE_SIZE).all()   # cap at 50 per page
    active_total = q.count()

    # Completed — paginated
    try:
        done_page = max(int(request.args.get('done_page', 1)), 1)
    except (ValueError, TypeError):
        done_page = 1
    done_offset  = (done_page - 1) * DONE_PAGE_SIZE
    done         = (Task.query.filter_by(user_id=u.id, completed=True)
                    .order_by(Task.completed_at.desc())
                    .limit(DONE_PAGE_SIZE).offset(done_offset).all())
    done_total   = Task.query.filter_by(user_id=u.id, completed=True).count()
    done_pages   = max((done_total + DONE_PAGE_SIZE - 1) // DONE_PAGE_SIZE, 1)

    priority_counts = {
        p: Task.query.filter_by(user_id=u.id, completed=False, priority=p).count()
        for p in ['CRITICAL', 'HIGH', 'MED', 'LOW']
    }

    return render_template('tasks.html',
        active=active, done=done, filter_priority=filter_p,
        priority_counts=priority_counts, today_str=today_str, confetti=confetti,
        active_total=active_total, active_page_size=ACTIVE_PAGE_SIZE,
        done_page=done_page, done_pages=done_pages, done_total=done_total,
        **user_stats(u), **shared_ctx(u),
    )


@tasks_bp.route('/complete_task/<int:id>', methods=['POST'], endpoint='complete_task')
@login_required
def complete_task(id):
    u    = current_user
    task = Task.query.filter_by(id=id, user_id=u.id).first_or_404()
    if not task.completed:
        task.complete()
        earned = award_xp(u, 10)
        award_credits(u, 50)
        db.session.commit()
        check_and_unlock(u)
        track('task_done', user_id=u.id)
        flash(f'+{earned} XP  +50 CR — "{task.title}" complete.', 'success')
    return redirect(url_for('tasks.tasks', confetti='1'))


@tasks_bp.route('/uncomplete_task/<int:id>', methods=['POST'], endpoint='uncomplete_task')
@login_required
def uncomplete_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    task.reopen()
    db.session.commit()
    flash(f'"{task.title}" moved back to active.', 'info')
    return redirect(url_for('tasks.tasks'))


@tasks_bp.route('/update_task_status/<int:id>', methods=['POST'], endpoint='update_task_status')
@login_required
def update_task_status(id):
    u      = current_user
    task   = Task.query.filter_by(id=id, user_id=u.id).first_or_404()
    status = (request.json.get('status', 'todo') if request.is_json
              else request.form.get('status', 'todo'))

    if status == 'done' and not task.completed:
        task.complete()
        earned = award_xp(u, 10)
        award_credits(u, 50)
        db.session.commit()
        check_and_unlock(u)
        track('task_done', user_id=u.id)
        return jsonify({'ok': True, 'xp': earned, 'cr': 50})
    elif status == 'inprogress':
        task.set_inprogress(); db.session.commit()
    else:
        task.reopen(); db.session.commit()
    return jsonify({'ok': True})


@tasks_bp.route('/delete/tasks/<int:id>', methods=['POST'], endpoint='delete_task')
@login_required
def delete_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    title = task.title
    db.session.delete(task); db.session.commit()
    flash(f'Task "{title}" deleted.', 'info')
    return redirect(request.referrer or url_for('tasks.tasks'))
