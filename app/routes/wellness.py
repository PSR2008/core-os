"""app/routes/wellness.py. Blueprint name: 'wellness'."""
from datetime import date
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.wellness import WellnessLog
from app.services.game_service import user_stats, shared_ctx
from . import Blueprint

wellness_bp = Blueprint('wellness', __name__)


@wellness_bp.route('/wellness', methods=['GET', 'POST'], endpoint='wellness')
@login_required
def wellness():
    u = current_user
    if request.method == 'POST':
        try:
            energy  = int(request.form.get('energy',  '5'))
            clarity = int(request.form.get('clarity', '5'))
            mood    = int(request.form.get('mood',    '5'))
        except ValueError:
            flash('Invalid biometric values.', 'error')
            return redirect(url_for('wellness.wellness'))

        if not all(1 <= v <= 10 for v in [energy, clarity, mood]):
            flash('All values must be between 1 and 10.', 'error')
            return redirect(url_for('wellness.wellness'))

        notes = request.form.get('notes', '').strip()[:500]
        try:
            db.session.add(WellnessLog(
                user_id=u.id, date=date.today(),
                energy=energy, clarity=clarity, mood=mood,
                notes=notes or None,
            ))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Biometrics already logged today. Delete the existing entry first.', 'warning')
            return redirect(url_for('wellness.wellness'))

        from app.services.growth_service import track
        track('wellness_log', user_id=u.id)
        avg = round((energy + clarity + mood) / 3, 1)
        flash(f'Biometrics logged — avg score {avg}/10.', 'success')
        return redirect(url_for('wellness.wellness'))

    logs = (WellnessLog.query.filter_by(user_id=u.id)
            .order_by(WellnessLog.id.desc()).limit(15).all())
    return render_template('wellness.html', logs=logs, **user_stats(u), **shared_ctx(u))


@wellness_bp.route('/delete/wellness/<int:id>', methods=['POST'], endpoint='delete_wellness')
@login_required
def delete_wellness(id):
    log = WellnessLog.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    flash('Wellness entry deleted.', 'info')
    return redirect(request.referrer or url_for('wellness.wellness'))
