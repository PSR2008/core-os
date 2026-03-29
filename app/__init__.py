"""
app/__init__.py — Application factory.

Database initialisation strategy
──────────────────────────────────
development (SQLite)
  • If tables exist → use as-is (normal restarts).
  • If tables are missing → call db.create_all() automatically.
    This means `python run.py` on a fresh clone just works without
    requiring the developer to run `flask db init/migrate/upgrade` first.
    Flask-Migrate is still available for schema evolution; the auto-create
    is only a first-run convenience.

production (PostgreSQL / hosted DB)
  • If tables exist → use as-is.
  • If tables are missing → auto-create them so first deploy can boot even
    on platforms where pre-deploy migration commands or shell access are not
    available on the chosen plan.
  • This is practical for Render free-tier style deployment.
  • Later, when moving to a more professional paid setup, you can switch
    back to strict migration-only enforcement.

testing (in-memory SQLite)
  • db.create_all() always runs; migrations are never used.

Seeding (shop items + achievements)
  • Wrapped in OperationalError guards — safe even if tables somehow don't
    exist at seed time.
"""
import os
import logging
import importlib

from flask import Flask, render_template, request as flask_request
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import OperationalError

from config import get_config
from app.extensions import db, migrate, login_manager, csrf, limiter


def create_app(cfg=None):
    flask_app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    )

    flask_app.config.from_object(cfg or get_config())
    _run_startup_checks(flask_app)
    _setup_logging(flask_app)

    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login_manager.init_app(flask_app)
    csrf.init_app(flask_app)
    limiter.init_app(flask_app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Authentication required to access CORE OS.'
    login_manager.login_message_category = 'warning'

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    @flask_app.after_request
    def _log_request(response):
        if not flask_app.config.get('TESTING'):
            flask_app.logger.info(
                '%s %s %s — %s',
                flask_request.method,
                flask_request.path,
                flask_request.remote_addr,
                response.status_code,
            )
        return response

    # ── Blueprints ────────────────────────────────────────────────────────────
    from app.routes.auth import auth_bp
    from app.routes.entrance import entrance_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.tasks import tasks_bp
    from app.routes.habits import habits_bp
    from app.routes.expenses import expenses_bp
    from app.routes.wellness import wellness_bp
    from app.routes.shop import shop_bp
    from app.routes.profile import profile_bp
    from app.routes.api import api_bp
    from app.routes.share import share_bp
    from app.routes.growth import growth_bp
    from app.routes.legal import legal_bp

    for bp in [
        auth_bp,
        entrance_bp,
        dashboard_bp,
        tasks_bp,
        habits_bp,
        expenses_bp,
        wellness_bp,
        shop_bp,
        profile_bp,
        api_bp,
        share_bp,
        growth_bp,
        legal_bp,
    ]:
        flask_app.register_blueprint(bp)

    # ── Error handlers ────────────────────────────────────────────────────────
    @flask_app.errorhandler(403)
    def forbidden(e):
        flask_app.logger.warning(
            '403 Forbidden: %s %s',
            flask_request.method,
            flask_request.path,
        )
        return render_template('errors/403.html'), 403

    @flask_app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @flask_app.errorhandler(429)
    def rate_limited(e):
        flask_app.logger.warning(
            '429 Rate limited: %s from %s',
            flask_request.path,
            flask_request.remote_addr,
        )
        if flask_request.is_json or flask_request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'status': 'error', 'error': 'Rate limit exceeded.'}), 429

        from flask import flash, redirect
        flash('Too many requests. Please slow down.', 'error')
        return redirect(flask_request.referrer or '/login'), 429

    @flask_app.errorhandler(500)
    def server_error(e):
        flask_app.logger.error('500 Internal Server Error: %s', str(e), exc_info=True)
        return render_template('errors/500.html'), 500

    # ── Schema initialisation + seed ──────────────────────────────────────────
    with flask_app.app_context():
        importlib.import_module('app.models')
        _init_db(flask_app)
        _seed_reference_data(flask_app)

    return flask_app


# ── Database initialisation ───────────────────────────────────────────────────

def _tables_exist() -> bool:
    """Return True if the core schema (users table) already exists."""
    try:
        inspector = sa_inspect(db.engine)
        return inspector.has_table('users')
    except Exception:
        return False


def _init_db(flask_app: Flask) -> None:
    """
    Ensure the database schema exists.

    Environment behaviour
    ─────────────────────
    testing      → always create via db.create_all() (in-memory, no migrations)
    development  → auto-create if tables are absent
    production   → auto-create if tables are absent (for first deploy on limited
                   hosting plans where migrations cannot be run manually)
    """
    env = os.environ.get('FLASK_ENV', 'development')

    if env == 'testing':
        db.create_all()
        flask_app.logger.debug('Testing: schema created with db.create_all()')
        return

    if _tables_exist():
        return

    if env == 'production':
        flask_app.logger.warning(
            'Tables missing in production — auto-creating with db.create_all()'
        )
        try:
            db.create_all()
            flask_app.logger.info('Production schema created successfully')
        except Exception as exc:
            flask_app.logger.error('db.create_all() failed in production: %s', exc)
            raise
        return

    # Development / default
    flask_app.logger.warning(
        'Database tables not found — running db.create_all() for first-time setup. '
        'For schema migrations use `flask db migrate` and `flask db upgrade`.'
    )
    try:
        db.create_all()
        flask_app.logger.info('Schema created successfully via db.create_all()')
    except Exception as exc:
        flask_app.logger.error('db.create_all() failed: %s', exc)
        raise


# ── Seed reference data ───────────────────────────────────────────────────────

def _seed_reference_data(flask_app: Flask) -> None:
    """
    Seed shop items and achievements.
    Each seed call is wrapped individually so one failure does not block the
    other, and neither blocks the app from starting.
    """
    from app.services.shop_service import seed_shop_items
    from app.services.achievement_service import seed_achievements

    try:
        seed_shop_items()
    except OperationalError:
        db.session.rollback()
        flask_app.logger.warning(
            'seed_shop_items() skipped — shop_items table not found. '
            'This resolves automatically after schema creation.'
        )

    try:
        seed_achievements()
    except OperationalError:
        db.session.rollback()
        flask_app.logger.warning(
            'seed_achievements() skipped — achievements table not found. '
            'This resolves automatically after schema creation.'
        )


# ── Startup checks ────────────────────────────────────────────────────────────

def _run_startup_checks(flask_app: Flask) -> None:
    env = os.environ.get('FLASK_ENV', 'development')
    from app.services.startup_checks import run_production_checks, run_development_checks

    if env == 'production':
        run_production_checks()
    else:
        run_development_checks()


# ── Logging setup ─────────────────────────────────────────────────────────────

def _setup_logging(flask_app: Flask) -> None:
    log_level = logging.DEBUG if flask_app.config.get('DEBUG') else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] %(levelname)-8s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    flask_app.logger.setLevel(log_level)

    if not flask_app.config.get('DEBUG'):
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        log_file = os.environ.get('LOG_FILE')
        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.WARNING)
            fh.setFormatter(logging.Formatter(
                '[%(asctime)s] %(levelname)-8s %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            ))
            flask_app.logger.addHandler(fh)