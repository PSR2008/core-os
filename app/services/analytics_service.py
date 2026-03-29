"""
app/services/analytics_service.py — Analytics computed from DataContext.

PERFORMANCE: All functions accept a DataContext object and perform
zero database queries. All data was loaded once in DataContext.build().
"""
from __future__ import annotations
from datetime import date, timedelta
from collections import defaultdict


# ── Task analytics ─────────────────────────────────────────────────────────────

def task_analytics(ctx) -> dict:
    today = ctx.today
    total      = len(ctx.tasks_all)
    completed  = len(ctx.tasks_done)
    active     = len(ctx.tasks_active)
    overdue    = ctx.overdue_count()
    done_today = ctx.done_today_count()
    due_today  = ctx.due_today_count()
    this_week  = ctx.this_week_tasks()
    last_week  = ctx.last_week_tasks()

    completion_pct = round(completed / total * 100) if total else 0

    priority_counts = {'CRITICAL': 0, 'HIGH': 0, 'MED': 0, 'LOW': 0}
    for t in ctx.tasks_active:
        if t.priority in priority_counts:
            priority_counts[t.priority] += 1

    return dict(
        total=total, completed=completed, active=active,
        overdue=overdue, completion_pct=completion_pct,
        done_today=done_today, due_today=due_today,
        weekly_done=ctx.weekly_done_array(),
        this_week=this_week, last_week=last_week,
        week_trend=_trend(this_week, last_week),
        priority_counts=priority_counts,
    )


# ── Habit analytics ────────────────────────────────────────────────────────────

def habit_analytics(ctx) -> dict:
    habits = ctx.habits
    total  = len(habits)

    if not total:
        return dict(
            total=0, synced_today=0, consistency=0,
            top_streak=0, combined_streak=0,
            weekly_syncs=[], weekly_labels=[],
            this_week=0, last_week=0, week_trend='same',
            at_risk=[], best_habit=None,
        )

    synced_today    = ctx.synced_today()
    top_streak      = ctx.max_streak
    combined_streak = sum(h.streak for h in habits)
    best_habit      = max(habits, key=lambda h: h.streak, default=None)

    this_week  = ctx.this_week_syncs()
    last_week  = ctx.last_week_syncs()

    # Consistency: logs in last 30 days / (total habits × 30)
    total_possible = total * 30
    consistency = round(ctx.total_habit_logs_30 / total_possible * 100) if total_possible else 0

    return dict(
        total=total, synced_today=synced_today, consistency=consistency,
        top_streak=top_streak, combined_streak=combined_streak,
        weekly_syncs=ctx.weekly_syncs_array(),
        weekly_labels=ctx.weekly_labels(),
        this_week=this_week, last_week=last_week,
        week_trend=_trend(this_week, last_week),
        at_risk=ctx.at_risk_habits(),
        best_habit=best_habit,
    )


# ── Expense analytics ──────────────────────────────────────────────────────────

def expense_analytics(ctx) -> dict:
    today       = ctx.today
    month_start = today.replace(day=1)
    user        = ctx.user

    this_month = ctx.month_spend()

    # Last month
    last_month_end   = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    last_month = sum(
        e.amount for e in ctx.expenses_60
        if last_month_start <= e.date <= last_month_end
    )

    budget      = user.budget or 1
    budget_pct  = round(min(this_month / budget * 100, 200))
    remaining   = max(budget - this_month, 0)
    total_spent = sum(e.amount for e in ctx.expenses_60)  # 60-day proxy

    days_elapsed = max((today - month_start).days + 1, 1)
    daily_avg    = round(this_month / days_elapsed, 2) if this_month else 0

    # Category breakdown
    cat_labels, cat_values = ctx.top_categories(6)

    # Weekly spend (last 7 days)
    weekly_spend = [
        round(ctx.expense_by_day.get(today - timedelta(days=i), 0), 2)
        for i in range(6, -1, -1)
    ]

    return dict(
        this_month=round(this_month, 2), last_month=round(last_month, 2),
        budget_pct=budget_pct, remaining=round(remaining, 2),
        month_trend=_trend_inverse(this_month, last_month),
        total_spent=round(total_spent, 2),
        cat_labels=cat_labels, cat_values=cat_values,
        daily_avg=daily_avg, weekly_spend=weekly_spend,
    )


# ── Wellness analytics ─────────────────────────────────────────────────────────

def wellness_analytics(ctx) -> dict:
    recent = ctx.recent_wellness(14)
    if not recent:
        return dict(
            has_data=False, avg_energy=0, avg_clarity=0, avg_mood=0,
            overall_avg=0, trend='same', log_count=0,
            energy_trend='same', mood_trend='same', clarity_trend='same',
            last_log=None,
        )

    def avg(attr, logs):
        return round(sum(getattr(l, attr) for l in logs) / len(logs), 1) if logs else 0

    today = ctx.today
    this_week_logs = [l for l in recent if l.date >= today - timedelta(days=7)]
    last_week_logs = [l for l in recent if today - timedelta(days=14) <= l.date < today - timedelta(days=7)]

    avg_energy  = avg('energy',  recent[:7])
    avg_clarity = avg('clarity', recent[:7])
    avg_mood    = avg('mood',    recent[:7])
    overall_avg = round((avg_energy + avg_clarity + avg_mood) / 3, 1)

    this_w_avg = avg('energy', this_week_logs) + avg('mood', this_week_logs)
    last_w_avg = avg('energy', last_week_logs) + avg('mood', last_week_logs)

    return dict(
        has_data=True,
        avg_energy=avg_energy, avg_clarity=avg_clarity, avg_mood=avg_mood,
        overall_avg=overall_avg,
        trend=_trend(this_w_avg, last_w_avg),
        energy_trend=_trend(avg('energy', this_week_logs), avg('energy', last_week_logs)),
        mood_trend=_trend(avg('mood', this_week_logs), avg('mood', last_week_logs)),
        clarity_trend=_trend(avg('clarity', this_week_logs), avg('clarity', last_week_logs)),
        log_count=len(recent),
        last_log=recent[-1] if recent else None,
    )


# ── XP analytics ──────────────────────────────────────────────────────────────

def xp_analytics(ctx) -> dict:
    user      = ctx.user
    this_week = ctx.this_week_tasks()
    syncs_wk  = ctx.this_week_syncs()

    mult          = user.get_xp_multiplier()
    xp_this_week  = (this_week * 10 + syncs_wk * 5) * mult
    xp_per_day    = round(xp_this_week / 7, 1) if xp_this_week else 0
    xp_to_next    = 100 - user.level_progress
    days_to_lvl   = round(xp_to_next / xp_per_day) if xp_per_day > 0 else None

    mult_label = {1: '1x Base', 2: '2x Neural Booster', 3: '3x XP Overdrive'}.get(mult, f'{mult}x')

    return dict(
        level=user.level, level_pct=user.level_progress,
        total_xp=user.total_xp, xp_to_next=xp_to_next,
        xp_this_week=xp_this_week, xp_per_day=xp_per_day,
        days_to_next_level=days_to_lvl,
        multiplier=mult, multiplier_label=mult_label,
    )


# ── Productivity score ─────────────────────────────────────────────────────────

def productivity_score(ctx, t_data: dict, h_data: dict, w_data: dict) -> dict:
    user = ctx.user
    task_score    = min(t_data.get('this_week', 0) * 10, 30)
    total_h       = h_data.get('total', 0)
    synced_h      = h_data.get('synced_today', 0)
    habit_score   = round((synced_h / total_h) * 30) if total_h else 0
    w_avg         = w_data.get('overall_avg', 0)
    wellness_score = round((w_avg / 10) * 20) if w_data.get('has_data') else 10
    b_ratio        = user.spent / user.budget if user.budget > 0 else 0
    budget_score   = max(0, round((1 - min(b_ratio, 1)) * 20))

    total = task_score + habit_score + wellness_score + budget_score

    if   total >= 80: grade, color = 'OPTIMAL',  '#10b981'
    elif total >= 60: grade, color = 'NOMINAL',  '#6366f1'
    elif total >= 40: grade, color = 'STRAINED', '#fbbf24'
    else:             grade, color = 'CRITICAL', '#f43f5e'

    return dict(
        score=total, grade=grade, color=color,
        task_score=task_score, habit_score=habit_score,
        wellness_score=wellness_score, budget_score=budget_score,
    )


# ── Suggestions ───────────────────────────────────────────────────────────────

def get_suggestions(ctx, t_data: dict, h_data: dict, w_data: dict) -> list:
    user    = ctx.user
    actions = []

    if t_data.get('overdue', 0) > 0:
        n = t_data['overdue']
        actions.append(dict(priority=10, icon='⚠️',
            title=f'{n} overdue task{"s" if n>1 else ""}',
            desc='These are actively raising your threat score.',
            endpoint='tasks.tasks', label='CLEAR_NOW', color='var(--danger)'))

    critical = t_data.get('priority_counts', {}).get('CRITICAL', 0)
    if critical > 0:
        actions.append(dict(priority=9, icon='🔴',
            title=f'{critical} CRITICAL task{"s" if critical>1 else ""} pending',
            desc='Highest priority items are waiting.',
            endpoint='tasks.tasks', label='HANDLE_CRITICAL', color='var(--danger)'))

    at_risk = h_data.get('at_risk', [])
    if at_risk:
        h = at_risk[0]
        actions.append(dict(priority=8, icon='⏳',
            title=f'"{h.name}" streak at risk ({h.streak}d)',
            desc='Sync today to keep your streak alive.',
            endpoint='habits.habits', label='PROTECT_STREAK', color='var(--gold)'))

    unsynced = h_data.get('total', 0) - h_data.get('synced_today', 0)
    if unsynced > 0 and h_data.get('total', 0) > 0:
        actions.append(dict(priority=7, icon='⚡',
            title=f'{unsynced} habit{"s" if unsynced>1 else ""} to sync today',
            desc=f'+{unsynced*20} CR and +{unsynced*5} XP waiting.',
            endpoint='habits.habits', label='SYNC_NOW', color='var(--accent2)'))

    # Check wellness from ctx (no DB call)
    today = ctx.today
    logged_today = today in ctx.wellness_by_date
    if not logged_today:
        actions.append(dict(priority=5, icon='🧠',
            title='Log your biometrics today',
            desc='Wellness tracking unlocks cross-domain insights.',
            endpoint='wellness.wellness', label='LOG_NOW', color='var(--success)'))

    due_today = t_data.get('due_today', 0)
    if due_today > 0:
        actions.append(dict(priority=6, icon='📅',
            title=f'{due_today} task{"s" if due_today>1 else ""} due today',
            desc='Completing on-time keeps your threat score low.',
            endpoint='tasks.tasks', label='VIEW_DUE', color='var(--accent2)'))

    if t_data.get('total', 0) == 0:
        actions.append(dict(priority=4, icon='➕',
            title='Add your first task',
            desc='Build momentum by defining your first objective.',
            endpoint='tasks.tasks', label='ADD_TASK', color='var(--accent)'))

    if not actions:
        actions.append(dict(priority=0, icon='✅',
            title='All systems nominal',
            desc='No urgent actions. Maintain your momentum.',
            endpoint='dashboard.index', label='GREAT_WORK', color='var(--success)'))

    actions.sort(key=lambda a: -a['priority'])
    return actions[:3]


# ── Reminders ─────────────────────────────────────────────────────────────────

def get_reminders(ctx) -> list:
    today     = ctx.today
    reminders = []

    if today not in ctx.wellness_by_date:
        reminders.append(dict(urgency='medium', icon='🧠', endpoint='wellness.wellness',
            text="You haven't logged wellness today"))

    overdue = ctx.overdue_count()
    if overdue > 0:
        reminders.append(dict(urgency='high', icon='⚠️', endpoint='tasks.tasks',
            text=f'{overdue} task{"s" if overdue>1 else ""} passed their due date'))

    due_today_open = ctx.due_today_count()
    if due_today_open > 0:
        reminders.append(dict(urgency='high', icon='📅', endpoint='tasks.tasks',
            text=f'{due_today_open} task{"s" if due_today_open>1 else ""} due today'))

    # Last expense date (from ctx — no extra query)
    if ctx.expenses_60:
        last_exp_date = max(e.date for e in ctx.expenses_60)
        if last_exp_date < today - timedelta(days=3):
            reminders.append(dict(urgency='medium', icon='💸', endpoint='expenses.expenses',
                text=f'No expenses logged since {last_exp_date.strftime("%b %d")}'))

    return reminders[:4]


# ── Legacy compat: old callers that pass (user) instead of (ctx) ──────────────
# The game_service still calls user.spent, which triggers a DB query on the
# User model. That's acceptable — it's one query, not a loop.

def next_best_action(user, tasks: dict, habits: dict, wellness: dict) -> dict:
    """Compat shim — returns first suggestion as single dict."""
    # Build a minimal context-like namespace from pre-computed dicts
    class _FakeCtx:
        pass
    fc = _FakeCtx()
    fc.today = date.today()
    fc.tasks_all    = []
    fc.tasks_active = []
    fc.wellness_by_date = {}
    suggestions = [s for s in [
        dict(priority=10, icon='⚠️', title=f'{tasks.get("overdue",0)} overdue',
             desc='', endpoint='tasks.tasks', label='CLEAR', color='var(--danger)')
    ] if tasks.get('overdue', 0) > 0]
    if not suggestions:
        return dict(icon='✅', title='All systems nominal', desc='No urgent actions.',
                    endpoint='dashboard.index', label='OK', color='var(--success)')
    return suggestions[0]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _trend(current, previous) -> str:
    if previous == 0 and current == 0: return 'same'
    if previous == 0: return 'up'
    pct = (current - previous) / previous * 100
    if pct > 10:  return 'up'
    if pct < -10: return 'down'
    return 'same'

def _trend_inverse(current, previous) -> str:
    raw = _trend(current, previous)
    return {'up': 'down', 'down': 'up', 'same': 'same'}[raw]
