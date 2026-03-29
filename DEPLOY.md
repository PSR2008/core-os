# CORE OS — Deployment Guide (v11)

## Quick Start (Development)

```bash
cd core_os
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Set SECRET_KEY in .env

flask db init
flask db migrate -m "initial schema"
flask db upgrade
python run.py
```

Visit http://localhost:5000 → register → 3-step onboarding → dashboard.

---

## Upgrading from v10 to v11

If you have an existing database from a prior version:

```bash
pip install -r requirements.txt

flask db migrate -m "v11 perf indexes and growth models"
flask db upgrade
```

New schema additions:
- `users`: `referral_code`, `referred_by_id`, `onboarding_step`, `is_premium`,
  `weekly_task_goal`, `weekly_habit_goal`
- `achievements`: `tier` column
- New tables: `user_feedback`, `growth_events`
- Compound indexes on `tasks`, `habits`, `habit_logs`, `expenses`, `wellness_logs`

---

## Production (Render / Railway / Heroku)

### Required environment variables

| Variable | Value |
|---|---|
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | PostgreSQL URL from platform |
| `FLASK_ENV` | `production` |
| `RATELIMIT_STORAGE_URI` | Redis URL (`redis://...`) |
| `MAIL_SERVER` | `smtp.gmail.com` |
| `MAIL_USERNAME` | Your email |
| `MAIL_PASSWORD` | Gmail App Password |

### Deploy steps

```bash
# 1. Set all environment variables in your platform dashboard

# 2. Run migrations (pre-deploy command)
flask db upgrade

# 3. Start (Procfile handles this automatically)
gunicorn run:app --workers 2 --threads 2 --timeout 60 --bind 0.0.0.0:$PORT
```

---

## Performance Summary (v11)

| Metric | Before | After |
|---|---|---|
| Dashboard DB queries | ~180 | ~12-15 |
| Heatmap queries (habits) | N × 30 | 1 |
| Inventory queries per page | 1 + N | 2 (selectinload) |
| Compound DB indexes | 0 | 14 |
| API pagination | No | Yes (20/page default) |

---

## Granting Premium Access (manual, for testing)

```bash
flask shell
>>> from app.models.user import User
>>> from app.extensions import db
>>> u = User.query.filter_by(username='youruser').first()
>>> u.is_premium = True
>>> db.session.commit()
```

---

## API Reference (v11)

All endpoints require authentication (session cookie). JSON in/out.

### Response format
```json
{ "status": "ok", "data": {...} }
{ "status": "ok", "data": { "items": [...], "page": 1, "pages": 5, "total": 92 } }
{ "status": "error", "error": "message" }
```

### Endpoints
```
GET  /api/stats                  — user stats + threat score
GET  /api/v1/me                  — full user profile
PATCH /api/v1/me                 — update operative_name, age, budget

GET  /api/v1/tasks               — list tasks (?page=1&per_page=20&status=active)
POST /api/v1/tasks               — create task
GET  /api/v1/tasks/<id>          — get task
PUT  /api/v1/tasks/<id>          — update task (title, priority, status, due_date)
DELETE /api/v1/tasks/<id>        — delete task

GET  /api/v1/habits              — list habits
POST /api/v1/habits              — create habit
GET  /api/v1/habits/<id>         — get habit
POST /api/v1/habits/<id>/sync    — sync habit for today (awards XP/CR)
DELETE /api/v1/habits/<id>       — delete habit

GET  /api/v1/expenses            — list expenses (?page=1&per_page=20)
POST /api/v1/expenses            — create expense
DELETE /api/v1/expenses/<id>     — delete expense

GET  /api/v1/wellness            — list wellness logs
POST /api/v1/wellness            — create wellness log
DELETE /api/v1/wellness/<id>     — delete wellness log
```

### Share card
```
GET /share/<username>  — public share card (no auth required)
GET /share/me          — redirect to your own share card
```

### Referral
```
GET /ref/<code>  — referral landing, stores code in session, redirects to register
```
