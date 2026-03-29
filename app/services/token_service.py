"""
app/services/token_service.py — Signed token generation and verification.

Uses itsdangerous URLSafeTimedSerializer — no DB table needed.
Used for password reset links emailed to the user.
The token encodes the user's email and expires after MAX_AGE seconds.
"""
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app

_SALT_RESET = 'password-reset-salt-v1'
MAX_AGE     = 3600   # 1 hour


def generate_reset_token(email: str) -> str:
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email.lower(), salt=_SALT_RESET)


def verify_reset_token(token: str) -> str | None:
    """
    Returns the email address if token is valid and not expired.
    Returns None if the token is invalid or expired.
    """
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt=_SALT_RESET, max_age=MAX_AGE)
        return email
    except (SignatureExpired, BadSignature):
        return None
