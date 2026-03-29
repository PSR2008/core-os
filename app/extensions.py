"""
app/extensions.py — Flask extension singletons.

Limiter storage reads RATELIMIT_STORAGE_URI from environment.
Set it to redis://... in production for multi-worker safety.
Defaults to memory:// (single-process dev only).
"""
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate     import Migrate
from flask_login       import LoginManager
from flask_wtf.csrf    import CSRFProtect
from flask_limiter     import Limiter
from flask_limiter.util import get_remote_address

db            = SQLAlchemy()
migrate       = Migrate()
login_manager = LoginManager()
csrf          = CSRFProtect()
limiter       = Limiter(
    key_func   = get_remote_address,
    default_limits = [],
    storage_uri = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'),
)
