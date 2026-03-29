"""
config.py — CORE OS environment configuration.

Three environments:
  development  SQLite, memory rate-limiter, console email, debug on
  testing      in-memory SQLite, no CSRF, fast startup
  production   PostgreSQL required, Redis required, SMTP required, debug off
               Validation is enforced by startup_checks.py, not here.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Base settings shared across all environments."""
    SECRET_KEY               = os.environ.get('SECRET_KEY') or os.urandom(32)
    WTF_CSRF_ENABLED         = True
    WTF_CSRF_TIME_LIMIT      = 3600              # CSRF tokens valid 1 hour
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400 * 14      # 14-day remember-me
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES      = False
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024         # 1 MB request body cap

    # NOTE: No SQLALCHEMY_ENGINE_OPTIONS here.
    # SQLite does not support pool_timeout/pool_recycle/pool_pre_ping.
    # Each subclass defines only what its database driver supports.


class DevelopmentConfig(Config):
    DEBUG                 = True
    TESTING               = False
    SESSION_COOKIE_SECURE = False    # allow http:// in local dev

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL')
        or f'sqlite:///{os.path.join(BASE_DIR, "coreos_dev.db")}'
    )

    # SQLite-safe: only check_same_thread (needed for Flask dev server threads)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
    }


class ProductionConfig(Config):
    DEBUG                 = False
    TESTING               = False
    SESSION_COOKIE_SECURE = True     # HTTPS-only cookie
    PREFERRED_URL_SCHEME  = 'https'

    # PostgreSQL connection pool — invalid for SQLite, only used here
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,   # test connection health before checkout
        'pool_recycle':  300,    # recycle idle connections every 5 minutes
        'pool_timeout':  20,     # give up waiting for connection after 20s
        'pool_size':     5,      # keep 5 persistent connections
        'max_overflow':  10,     # allow 10 extra connections under load
    }

    @staticmethod
    def _fix_pg_url(url: str) -> str:
        """Heroku/Render supply postgres:// — SQLAlchemy needs postgresql://"""
        if url.startswith('postgres://'):
            return url.replace('postgres://', 'postgresql://', 1)
        return url

    # DATABASE_URL is set after startup validation in startup_checks.py
    # This default is intentionally empty — validation will catch it.
    SQLALCHEMY_DATABASE_URI = _fix_pg_url.__func__(
        os.environ.get('DATABASE_URL', '')
    )


class TestingConfig(Config):
    """
    In-memory SQLite for automated tests.
    CSRF disabled so test clients can POST without tokens.
    db.create_all() is called by create_app() only in this environment.
    """
    TESTING               = True
    DEBUG                 = False
    WTF_CSRF_ENABLED      = False
    SESSION_COOKIE_SECURE = False
    SECRET_KEY            = 'test-secret-key-not-for-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # StaticPool keeps the same connection for the lifetime of the test.
    # connect_args check_same_thread=False required for SQLite + threading.
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
    }


config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}


def get_config() -> type:
    """
    Return the config class for the current FLASK_ENV.
    Production startup validation is handled separately in startup_checks.py
    so that the Flask app object exists before we raise errors (enabling
    better error reporting).
    """
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
