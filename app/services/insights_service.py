"""
app/services/insights_service.py — Rule-based intelligence engine.

Performance: All rules now accept a DataContext and read from its
pre-loaded Python structures. Zero DB queries per insight generation.

Insight schema: { icon, title, body, type, category, confidence }
"""
from __future__ import annotations
from datetime import date, timedelta
from collections import defaultdict


_MIN_TASKS    = 8
_MIN_HABITS   = 5
_MIN_EXPENSES = 6
_MIN_WELLNESS = 5


def generate_insights(user, ctx=None) -> list[dict]:
    """
    Run all insight rules. Uses DataContext if provided (fast path).
    Falls back to direct DB queries for backward compatibility.
    """
    if ctx is None:
        # Legacy path — build a minimal context
        from app.services.data_context import DataContext
        ctx = DataContext.build(user)

    results = []
    results += _rule_weekend_productivity(ctx)
    results += _rule_critical_avoidance(ctx)
    results += _rule_habit_best_day(ctx)
    results += _rule_habit_break_pattern(ctx)
    results += _rule_expense_category_dominance(ctx)
    results += _rule_budget_pace(ctx)
    results += _rule_wellness_decline(ctx)
    results += _rule_low_energy_pattern(ctx)
    results += _rule_spend_mood_correlation(ctx)
    results += _rule_task_wellness_correlation(ctx)
    results += _rule_habit_improvement(ctx)
    results += _rule_streak_achievement(ctx)

    seen_cats = {}
    for ins in results:
        cat = ins['category']
        if cat not in seen_cats or (ins['confidence'] == 'high' and seen_cats[cat]['confidence'] != 'high'):
            seen_cats[cat] = ins

    ordered = sorted(seen_cats.values(), key=lambda x: (
        0 if x['confidence'] == 'high' else 1,
        0 if x['type'] == 'warning'  else
        1 if x['type'] == 'pattern'  else
        2 if x['type'] == 'positive' else 3,
    ))
    return ordered[:5]


# ── All rules read from ctx — no DB calls ─────────────────────────────────────

def _rule_weekend_productivity(ctx) -> list:
    tasks_done = ctx.tasks_done
    if len(tasks_done) < _MIN_TASKS:
        return []

    weekday_count = sum(1 for t in tasks_done
                        if t.completed_at and t.completed_at.weekday() < 5)
    weekend_count = sum(1 for t in tasks_done
                        if t.completed_at and t.completed_at.weekday() >= 5)

    wd_rate = weekday_count / 43
    we_rate = weekend_count / 17
    if wd_rate < 0.1 or we_rate < 0.1:
        return []

    drop_pct = round((wd_rate - we_rate) / wd_rate * 100)
    if drop_pct >= 40:
        return [dict(icon='📉', category='tasks', confidence='high', type='pattern',
            title='Productivity drops on weekends',
            body=(f'You complete {drop_pct}% fewer tasks on weekends vs weekdays. '
                  f'Adding even 1 task on Saturdays could meaningfully lift your weekly score.'))]
    if drop_pct <= -30:
        return [dict(icon='📈', category='tasks', confidence='medium', type='positive',
            title='Weekends are your power sessions',
            body=(f'You complete {abs(drop_pct)}% more tasks per day on weekends. '
                  f'Consider front-loading harder tasks to your weekend.'))]
    return []


def _rule_critical_avoidance(ctx) -> list:
    today = ctx.today
    old_critical = sum(
        1 for t in ctx.tasks_active
        if t.priority == 'CRITICAL' and t.created_at
        and (t.created_at.date() if hasattr(t.created_at, 'date') else t.created_at) <= today - timedelta(days=3)
    )
    if old_critical >= 2:
        return [dict(icon='🔴', category='tasks', confidence='high', type='warning',
            title=f'{old_critical} critical tasks stalled for 3+ days',
            body='CRITICAL items older than 3 days are the biggest driver of your threat score.')]
    return []


def _rule_habit_best_day(ctx) -> list:
    if len(ctx.habit_logs_60) < _MIN_HABITS:
        return []

    day_counts = defaultdict(int)
    for log in ctx.habit_logs_60:
        day_counts[log.date_logged.weekday()] += 1

    if not day_counts: return []
    best  = max(day_counts, key=day_counts.get)
    worst = min(day_counts, key=day_counts.get)
    day_names = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

    if day_counts[best] >= day_counts[worst] * 2:
        return [dict(icon='📅', category='habits', confidence='medium', type='pattern',
            title=f'{day_names[best]}s are your strongest habit day',
            body=(f'You sync habits {day_counts[best]} times on {day_names[best]}s '
                  f'vs {day_counts[worst]} on {day_names[worst]}s.'))]
    return []


def _rule_habit_break_pattern(ctx) -> list:
    if len(ctx.habit_logs_60) < _MIN_HABITS:
        return []

    log_dates = sorted({log.date_logged for log in ctx.habit_logs_60})
    if len(log_dates) < 7: return []

    all_dates = {log_dates[0] + timedelta(days=i)
                 for i in range((log_dates[-1] - log_dates[0]).days + 1)}
    gap_days  = all_dates - set(log_dates)
    if not gap_days: return []

    gap_weekdays = defaultdict(int)
    for d in gap_days:
        gap_weekdays[d.weekday()] += 1

    weakest   = max(gap_weekdays, key=gap_weekdays.get)
    day_names = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    if gap_weekdays[weakest] >= 3:
        return [dict(icon='⚠️', category='habits', confidence='medium', type='warning',
            title=f'{day_names[weakest]}s are your habit weak spot',
            body=f"You've missed habits on {gap_weekdays[weakest]} {day_names[weakest]}s in 60 days.")]
    return []


def _rule_habit_improvement(ctx) -> list:
    if len(ctx.habit_logs_60) < 10: return []
    this_week = ctx.this_week_syncs()
    last_week = ctx.last_week_syncs()
    if last_week == 0: return []
    if this_week >= last_week * 1.3:
        uplift = round((this_week - last_week) / last_week * 100)
        return [dict(icon='🔥', category='habits', confidence='high', type='positive',
            title='Habit consistency is improving',
            body=f'You synced {this_week} habits this week vs {last_week} last week — a {uplift}% uplift.')]
    return []


def _rule_streak_achievement(ctx) -> list:
    if ctx.max_streak >= 14:
        return [dict(icon='🏆', category='habits', confidence='high', type='positive',
            title=f'You have a {ctx.max_streak}-day habit streak',
            body=f'A {ctx.max_streak}-day streak puts you in the top tier of CORE OS users.')]
    return []


def _rule_expense_category_dominance(ctx) -> list:
    if len(ctx.expenses_60) < _MIN_EXPENSES: return []
    total = sum(ctx.cat_totals.values())
    if not total: return []
    top_cat = max(ctx.cat_totals, key=ctx.cat_totals.get)
    top_pct = round(ctx.cat_totals[top_cat] / total * 100)
    if top_pct >= 55:
        return [dict(icon='💸', category='expenses', confidence='high', type='pattern',
            title=f'{top_cat!r} is {top_pct}% of your spending',
            body=(f'Over 60 days, {top_cat} makes up {top_pct}% of all tracked expenses. '
                  f'Consider whether this aligns with your priorities.'))]
    return []


def _rule_budget_pace(ctx) -> list:
    user   = ctx.user
    today  = ctx.today
    if user.budget <= 0: return []
    month_start  = today.replace(day=1)
    this_month   = ctx.month_spend()
    days_elapsed = max((today - month_start).days + 1, 1)
    projected    = (this_month / days_elapsed) * 30
    if projected > user.budget * 1.15:
        over_pct = round((projected - user.budget) / user.budget * 100)
        return [dict(icon='📊', category='expenses', confidence='high', type='warning',
            title=f'On track to exceed budget by {over_pct}%',
            body=(f'At your current daily rate you are projected to exceed '
                  f'your monthly budget by {over_pct}%. Consider slowing discretionary spend.'))]
    return []


def _rule_wellness_decline(ctx) -> list:
    recent = ctx.recent_wellness(5)
    if len(recent) < _MIN_WELLNESS: return []
    scores = [(r.energy + r.clarity + r.mood) / 3 for r in recent]
    declining = all(scores[i] <= scores[i-1] for i in range(1, len(scores)))
    if declining and scores[-1] < 5:
        avg = round(sum(scores) / len(scores), 1)
        return [dict(icon='📉', category='wellness', confidence='high', type='warning',
            title='Wellness has been declining for 5 sessions',
            body=f'Your last 5 logs average {avg}/10 and are trending down.')]
    return []


def _rule_low_energy_pattern(ctx) -> list:
    recent = ctx.recent_wellness(10)
    if len(recent) < _MIN_WELLNESS: return []
    low = [r for r in recent if r.energy <= 4]
    if len(low) >= 6:
        return [dict(icon='🔋', category='wellness', confidence='medium', type='pattern',
            title='Consistently low energy in recent sessions',
            body=f'{len(low)} of your last 10 logs show energy ≤4/10.')]
    return []


def _rule_spend_mood_correlation(ctx) -> list:
    if len(ctx.expenses_60) < _MIN_EXPENSES or len(ctx.wellness_60) < _MIN_WELLNESS:
        return []

    paired = [
        ((w.energy + w.mood) / 2, ctx.expense_by_day.get(w.date, 0))
        for w in ctx.wellness_60
        if w.date in ctx.expense_by_day
    ]
    if len(paired) < 4: return []

    low_mood  = [s for m, s in paired if m <= 4.5]
    high_mood = [s for m, s in paired if m >= 6.5]
    if not low_mood or not high_mood: return []

    avg_low  = sum(low_mood)  / len(low_mood)
    avg_high = sum(high_mood) / len(high_mood)
    if avg_low >= avg_high * 1.35:
        spend_diff_pct = round((avg_low - avg_high) / avg_high * 100)
        return [dict(icon='🧠', category='cross', confidence='high', type='pattern',
            title='You spend more when your mood is low',
            body=(f'On low-mood days you spend {spend_diff_pct}% more on average '
                  f'than on high-mood days. Pattern detected from your real expense and wellness data.'))]
    return []


def _rule_task_wellness_correlation(ctx) -> list:
    if len(ctx.tasks_done) < _MIN_TASKS or len(ctx.wellness_60) < _MIN_WELLNESS:
        return []

    high_wellness_next = []
    low_wellness_next  = []
    for w in ctx.wellness_60:
        score    = (w.energy + w.clarity + w.mood) / 3
        next_day = w.date + timedelta(days=1)
        next_cnt = ctx.tasks_done_by_day.get(next_day, 0)
        if score >= 7:
            high_wellness_next.append(next_cnt)
        elif score <= 4:
            low_wellness_next.append(next_cnt)

    if len(high_wellness_next) < 3 or len(low_wellness_next) < 3: return []

    avg_good = sum(high_wellness_next) / len(high_wellness_next)
    avg_bad  = sum(low_wellness_next)  / len(low_wellness_next)
    if avg_good >= avg_bad * 1.4:
        return [dict(icon='✨', category='cross', confidence='high', type='pattern',
            title='High wellness days predict productivity spikes',
            body=(f'After high-wellness sessions you complete {avg_good:.1f} tasks/day avg '
                  f'vs {avg_bad:.1f} after low-wellness days.'))]
    return []
