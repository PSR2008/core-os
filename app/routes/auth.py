"""app/routes/auth.py — Auth routes. Blueprint name: 'auth'."""
import re
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models.user import User

auth_bp = Blueprint('auth', __name__)   # name='auth' → endpoints: auth.login, auth.logout …

_EMAIL_RE    = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,32}$')


def _validate_register(username, email, password, confirm):
    errs = []
    if not _USERNAME_RE.match(username):
        errs.append('Username: 3–32 characters, letters/numbers/underscores only.')
    if not _EMAIL_RE.match(email):
        errs.append('Enter a valid email address.')
    if len(password) < 8:
        errs.append('Password must be at least 8 characters.')
    if password != confirm:
        errs.append('Passwords do not match.')
    return errs


@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
@limiter.limit('20 per minute; 5 per 10 seconds',
               error_message='Too many login attempts. Wait a moment.')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    error   = None
    prefill = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        prefill  = username

        if not username or not password:
            error = 'Username and password are required.'
        else:
            user = User.query.filter(
                db.func.lower(User.username) == username.lower()
            ).first()
            if user and user.check_password(password):
                login_user(user, remember=True)
                flash(f'Welcome back, {user.operative_name or user.username}.', 'success')
                next_url = request.args.get('next', '')
                if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                    return redirect(next_url)
                return redirect(url_for('dashboard.index'))
            error = 'Invalid credentials — access denied.'

    return render_template('auth/login.html', error=error, prefill=prefill)


@auth_bp.route('/register', methods=['GET', 'POST'], endpoint='register')
@limiter.limit('10 per minute',
               error_message='Too many registration attempts. Try again shortly.')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    errors = []
    form   = {}
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email',    '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm',  '')
        form     = {'username': username, 'email': email}

        errors = _validate_register(username, email, password, confirm)

        if not errors:
            if User.query.filter(db.func.lower(User.username) == username.lower()).first():
                errors.append('Username already taken.')
            elif User.query.filter(db.func.lower(User.email) == email.lower()).first():
                errors.append('Email already registered.')

        if not errors:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            # Generate permanent referral code for this user
            user.ensure_referral_code()

            # Process referral if a code was stored in session before registration
            from flask import session as _sess
            from app.services.referral_service import process_referral
            from app.services.growth_service   import track
            ref_code = _sess.pop('referral_code', None)
            if ref_code:
                process_referral(user, ref_code)
            track('register', user_id=user.id)

            login_user(user, remember=True)
            flash(f'Operative {username} initialized. Welcome to CORE OS.', 'success')
            return redirect(url_for('growth.onboarding'))

    return render_template('auth/register.html', errors=errors, form=form)


@auth_bp.route('/logout', methods=['POST'], endpoint='logout')
@login_required
def logout():
    logout_user()
    flash('Session terminated.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'], endpoint='forgot_password')
@limiter.limit('5 per hour', error_message='Too many reset requests. Try again later.')
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    sent = False
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not _EMAIL_RE.match(email):
            flash('Enter a valid email address.', 'error')
        else:
            user = User.query.filter(db.func.lower(User.email) == email).first()
            if user:
                from app.services.token_service import generate_reset_token
                from app.services.mail_service  import send_password_reset_email
                token     = generate_reset_token(user.email)
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                email_sent = send_password_reset_email(user.email, reset_url)
                if not email_sent:
                    import os as _os
                    if _os.environ.get('FLASK_ENV', 'development') == 'development':
                        flash(f'[DEV] Reset link (no SMTP): {reset_url}', 'info')
                        return redirect(url_for('auth.forgot_password'))
            sent = True

    return render_template('auth/forgot_password.html', sent=sent)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'], endpoint='reset_password')
@limiter.limit('10 per hour', error_message='Too many reset attempts.')
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    from app.services.token_service import verify_reset_token
    email = verify_reset_token(token)
    if not email:
        flash('Reset link is invalid or has expired. Request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter(db.func.lower(User.email) == email.lower()).first()
    if not user:
        flash('No account found for this reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))

    errors = []
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm',  '')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')
        if not errors:
            user.set_password(password)
            db.session.commit()
            flash('Password updated. You can now log in.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token, errors=errors)
