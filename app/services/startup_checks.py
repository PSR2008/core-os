"""
app/services/startup_checks.py — Production startup validation.

Called once during create_app() before anything else runs.
Raises RuntimeError immediately with a clear message if required
environment variables are missing in production.

This is the single source of truth for "what does production require?"
"""
import os


def _fail(var: str, reason: str) -> None:
    raise RuntimeError(
        f"\n\n[CORE OS] PRODUCTION STARTUP ABORTED\n"
        f"  Missing: {var}\n"
        f"  Reason:  {reason}\n"
        f"  Action:  Set this variable in your environment or .env file.\n"
        f"  See:     .env.example for all required variables.\n"
    )


def run_production_checks() -> None:
    """
    Validate all required environment variables for production.
    Raises RuntimeError on the first missing or misconfigured value.
    Call this early in create_app() before extensions are initialised.
    """
    # 1. SECRET_KEY — mandatory, must be stable across restarts
    secret_key = os.environ.get('SECRET_KEY', '')
    if not secret_key:
        _fail('SECRET_KEY',
              'Required for session signing. Generate with: '
              'python3 -c "import secrets; print(secrets.token_hex(32))"')

    if secret_key == 'change-me-generate-a-real-32-char-hex-key':
        _fail('SECRET_KEY',
              'Default placeholder detected. '
              'Generate a real key: python3 -c "import secrets; print(secrets.token_hex(32))"')

    # 2. DATABASE_URL — must point to PostgreSQL, not SQLite
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url:
        _fail('DATABASE_URL',
              'Required for production database. '
              'Set to your PostgreSQL connection string: '
              'postgresql://user:password@host:5432/coreos')

    if db_url.startswith('sqlite'):
        _fail('DATABASE_URL',
              'SQLite is not safe for production (no concurrent writes, '
              'no connection pooling). Use PostgreSQL.')

    # 3. RATELIMIT_STORAGE_URI — must be Redis for multi-worker correctness
    rate_uri = os.environ.get('RATELIMIT_STORAGE_URI', '')
    if not rate_uri:
        _fail('RATELIMIT_STORAGE_URI',
              'Required for rate limiting across multiple Gunicorn workers. '
              'Set to your Redis URL: redis://localhost:6379/0')

    if rate_uri == 'memory://':
        _fail('RATELIMIT_STORAGE_URI',
              'memory:// only works with a single process. '
              'Use Redis for production: redis://localhost:6379/0')

    # 4. SMTP credentials — required if password reset is enabled
    # Password reset is always enabled (routes exist), so SMTP must be configured.
    mail_server = os.environ.get('MAIL_SERVER', '')
    mail_user   = os.environ.get('MAIL_USERNAME', '')
    mail_pass   = os.environ.get('MAIL_PASSWORD', '')

    if not mail_server:
        _fail('MAIL_SERVER',
              'Required for password reset emails. '
              'Example: smtp.gmail.com — '
              'Or set DISABLE_PASSWORD_RESET=true to skip this check.')

    if not mail_user:
        _fail('MAIL_USERNAME',
              'Required for SMTP authentication. '
              'Set to your sending email address.')

    if not mail_pass:
        _fail('MAIL_PASSWORD',
              'Required for SMTP authentication. '
              'For Gmail, use an App Password from myaccount.google.com/apppasswords')


def run_development_checks() -> None:
    """
    Warn (but do not fail) about missing development recommendations.
    Prints to stderr — does not raise.
    """
    import sys
    warnings = []

    if not os.environ.get('SECRET_KEY'):
        warnings.append('SECRET_KEY not set — using random key (sessions reset on restart)')

    if not os.environ.get('RATELIMIT_STORAGE_URI'):
        warnings.append('RATELIMIT_STORAGE_URI not set — using memory:// (single-process only)')

    if not os.environ.get('MAIL_SERVER'):
        warnings.append('MAIL_SERVER not set — password reset links will print to console')

    if warnings:
        print('\n[CORE OS DEV] Configuration warnings:', file=sys.stderr)
        for w in warnings:
            print(f'  ⚠  {w}', file=sys.stderr)
        print('', file=sys.stderr)
