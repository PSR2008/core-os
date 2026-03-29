"""
app/services/identity_service.py — Operative Identity System.

Performance: All signals now read from DataContext (pre-loaded data).
Zero DB queries after ctx is passed in.
"""
from __future__ import annotations
from datetime import date, timedelta


def get_operative_title(user, ctx=None) -> dict:
    """
    Return the user's primary title. Uses ctx if provided (fast path).
    """
    if ctx is None:
        from app.services.data_context import DataContext
        ctx = DataContext.build(user)

    today = ctx.today
    total_done   = len(ctx.tasks_done)
    overdue      = ctx.overdue_count()
    max_streak   = ctx.max_streak
    synced_today = ctx.synced_today()

    # Habit consistency over 30 days
    total_h      = len(ctx.habits)
    habit_pct_30 = (ctx.total_habit_logs_30 / (total_h * 30) * 100) if total_h else 0

    # Wellness average (last 7 logs)
    recent_w = ctx.recent_wellness(7)
    avg_wellness = (
        round(sum((w.energy + w.clarity + w.mood) / 3 for w in recent_w) / len(recent_w), 1)
        if recent_w else 0
    )

    # Budget status
    budget_ok = user.budget > 0 and user.spent <= user.budget
    expense_count = len(ctx.expenses_60)

    # Evaluate rules in priority order
    if (user.total_xp >= 2000 and max_streak >= 21 and total_done >= 50
            and overdue == 0 and avg_wellness >= 7):
        return dict(title='System Architect', subtitle='Peak Performance Operative',
            icon='⚡', color='#fbbf24',
            basis=f'{total_done} tasks done, {max_streak}d streak, {user.total_xp} XP')

    if max_streak >= 30:
        return dict(title='Iron Operative', subtitle='Unbroken Discipline',
            icon='🏋️', color='#818cf8',
            basis=f'{max_streak}-day habit streak maintained')

    if total_done >= 30 and overdue == 0 and user.level >= 8:
        return dict(title='Focus Master', subtitle='Zero Drift, Full Throughput',
            icon='🎯', color='#22d3ee',
            basis=f'{total_done} tasks completed with zero overdue')

    if habit_pct_30 >= 70 and user.login_streak >= 7:
        return dict(title='Consistent Operator', subtitle='Daily Systems Online',
            icon='🔄', color='#10b981',
            basis=f'{round(habit_pct_30)}% habit rate, {user.login_streak}-day login streak')

    if len(recent_w) >= 5 and avg_wellness >= 7.5:
        return dict(title='Wellness Guardian', subtitle='Biometrics Optimised',
            icon='🧠', color='#6ee7b7',
            basis=f'{len(ctx.wellness_60)} wellness logs, avg {avg_wellness}/10')

    if budget_ok and user.spent >= 1000 and expense_count >= 10:
        return dict(title='Budget Guardian', subtitle='Financial Discipline Active',
            icon='💰', color='#fcd34d',
            basis=f'Within budget — {user.spent:,.0f} in expenses tracked')

    if max_streak >= 14:
        return dict(title='Streak Keeper', subtitle='Consistency Compounds',
            icon='🔥', color='#f97316',
            basis=f'{max_streak}-day habit streak')

    if total_done >= 20:
        return dict(title='Task Machine', subtitle='High-Output Operative',
            icon='⚙️', color='#a78bfa',
            basis=f'{total_done} tasks completed')

    if max_streak >= 7:
        return dict(title='Week Warrior', subtitle='Seven-Day Discipline',
            icon='🗓️', color='#34d399',
            basis=f'{max_streak}-day habit streak')

    if total_done >= 5 or user.login_streak >= 3:
        return dict(title='Rising Operative', subtitle='Systems Coming Online',
            icon='📡', color='#6366f1',
            basis=f'{total_done} tasks, {user.login_streak}-day streak')

    return dict(title='Recruit', subtitle='Beginning Deployment',
        icon='🚀', color='#64748b', basis='Just initialized')


def get_all_earned_titles(user, ctx=None) -> list[dict]:
    if ctx is None:
        from app.services.data_context import DataContext
        ctx = DataContext.build(user)

    total_done  = len(ctx.tasks_done)
    max_streak  = ctx.max_streak
    total_h     = len(ctx.habits)
    habit_pct   = (ctx.total_habit_logs_30 / (total_h * 30) * 100) if total_h else 0
    budget_ok   = user.budget > 0 and user.spent <= user.budget
    earned = []

    if total_done >= 5:
        earned.append(dict(title='Task Machine', icon='⚙️', color='#a78bfa',
                           desc=f'{total_done} tasks completed'))
    if max_streak >= 7:
        earned.append(dict(title='Week Warrior', icon='🗓️', color='#34d399',
                           desc=f'{max_streak}-day streak'))
    if max_streak >= 30:
        earned.append(dict(title='Iron Operative', icon='🏋️', color='#818cf8',
                           desc=f'{max_streak}-day streak'))
    if habit_pct >= 70 and user.login_streak >= 7:
        earned.append(dict(title='Consistent Operator', icon='🔄', color='#10b981',
                           desc=f'{round(habit_pct)}% habit consistency'))
    if len(ctx.wellness_60) >= 15:
        earned.append(dict(title='Wellness Guardian', icon='🧠', color='#6ee7b7',
                           desc=f'{len(ctx.wellness_60)} wellness sessions'))
    if budget_ok and len(ctx.expenses_60) >= 10:
        earned.append(dict(title='Budget Guardian', icon='💰', color='#fcd34d',
                           desc='Budget maintained'))
    return earned
