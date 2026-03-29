"""
app/routes/growth.py — Growth and user acquisition routes.

  GET  /ref/<code>         — referral landing (stores code in session)
  POST /feedback           — submit feedback/bug report
  GET  /onboarding         — multi-step guided onboarding
  POST /onboarding/step    — advance onboarding step
"""
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, session, flash, jsonify,
)
from flask_login import login_required, current_user
from app.extensions import db

growth_bp = Blueprint('growth', __name__)


# ── Referral landing ──────────────────────────────────────────────────────────

@growth_bp.route('/ref/<code>', endpoint='referral_landing')
def referral_landing(code: str):
    """
    Store the referral code in session and redirect to register.
    Works whether or not the user is already logged in.
    """
    from app.models.user import User
    referrer = User.query.filter_by(referral_code=code.upper()).first()

    if referrer and (not current_user.is_authenticated or current_user.id != referrer.id):
        session['referral_code'] = code.upper()
        flash(
            f'You were invited by {referrer.operative_name or referrer.username}. '
            f'Register now and get +{100} XP on signup!',
            'info',
        )

    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.register'))


# ── Onboarding ────────────────────────────────────────────────────────────────

@growth_bp.route('/onboarding', endpoint='onboarding')
@login_required
def onboarding():
    u = current_user
    if u.onboarding_complete:
        return redirect(url_for('dashboard.index'))
    u.ensure_referral_code()
    return render_template('onboarding.html',
        step=u.onboarding_step,
        operative_name=u.operative_name or '',
    )


@growth_bp.route('/onboarding/step', methods=['POST'], endpoint='onboarding_step')
@login_required
def onboarding_step():
    """
    Handle each onboarding step form submission.
    Step 1: save operative name
    Step 2: create first task (optional but encouraged)
    Step 3: create first habit (optional but encouraged)
    Submitting step 3 or clicking Skip completes onboarding.
    """
    from app.models.task  import Task
    from app.models.habit import Habit
    from app.services.game_service import award_xp, award_credits

    u    = current_user
    step = u.onboarding_step

    if step == 1:
        name = request.form.get('name', '').strip()
        if name and len(name) <= 60:
            u.operative_name = name
        u.onboarding_step = 2

    elif step == 2:
        title = request.form.get('task_title', '').strip()
        if title:
            task = Task(user_id=u.id, title=title, priority='MED')
            db.session.add(task)
            earned = award_xp(u, 10)
            award_credits(u, 50)
            flash(f'First task added! +{earned} XP +50 CR.', 'success')
        u.onboarding_step = 3

    elif step == 3:
        habit_name = request.form.get('habit_name', '').strip()
        if habit_name:
            habit = Habit(user_id=u.id, name=habit_name)
            db.session.add(habit)
            earned = award_xp(u, 5)
            award_credits(u, 20)
            flash(f'First habit initialized! +{earned} XP +20 CR.', 'success')
        u.onboarding_step = 0   # complete

    db.session.commit()

    if u.onboarding_step == 0:
        flash('CORE OS initialized. Welcome, Operative.', 'success')
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('growth.onboarding'))


# ── Feedback ──────────────────────────────────────────────────────────────────

@growth_bp.route('/feedback', methods=['POST'], endpoint='submit_feedback')
@login_required
def submit_feedback():
    from app.models.feedback import UserFeedback
    fb_type = request.form.get('fb_type', 'general')
    message = request.form.get('message', '').strip()
    page    = request.form.get('page', '').strip()[:100]

    if not message:
        flash('Feedback message cannot be empty.', 'error')
        return redirect(request.referrer or url_for('dashboard.index'))
    if len(message) > 2000:
        flash('Feedback too long (max 2000 characters).', 'error')
        return redirect(request.referrer or url_for('dashboard.index'))
    if fb_type not in ('bug', 'feature', 'general'):
        fb_type = 'general'

    db.session.add(UserFeedback(
        user_id=current_user.id,
        fb_type=fb_type,
        message=message,
        page=page or None,
    ))
    db.session.commit()
    flash('Feedback received. Thank you, Operative.', 'success')
    return redirect(request.referrer or url_for('dashboard.index'))
