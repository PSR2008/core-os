"""
app/services/data_context.py — Request-scoped data context.

THE KEY PERFORMANCE FIX.

Instead of each analytics service independently querying the DB,
DataContext does all heavy lifting in a small number of efficient
bulk queries, then makes the results available to every service
via plain Python structures.

Before: ~180 DB queries per dashboard load (7-day loops × multiple services)
After:  ~15 DB queries per dashboard load (flat bulk fetches, no loops)

Usage:
    ctx = DataContext.build(user)         # one call, runs all queries
    t   = task_analytics_fast(ctx)        # pure Python, zero DB
    h   = habit_analytics_fast(ctx)       # pure Python, zero DB
    ...
"""
from __future__ import annotations
from datetime import date, timedelta, datetime
from collections import defaultdict
from app.extensions import db


class DataContext:
    """
    Immutable snapshot of a user's data for a single request.
    All heavy DB work happens in build() — services consume ctx attributes.
    """
    __slots__ = (
        'user', 'today', 'today_14', 'today_60',
        'tasks_active', 'tasks_done', 'tasks_all',
        'habits', 'habit_logs_60',
        'expenses_60', 'wellness_60',
        'tasks_done_by_day',      # dict[date, int]
        'habit_logs_by_day',      # dict[date, int]
        'expense_by_day',         # dict[date, float]
        'wellness_by_date',       # dict[date, tuple(e,c,m)]
        'cat_totals',             # dict[str, float]
        'max_streak',             # int
        'total_habit_logs_30',    # int
        'achievements_unlocked',  # set[str]
    )

    @classmethod
    def build(cls, user) -> 'DataContext':
        from app.models.task     import Task
        from app.models.habit    import Habit, HabitLog
        from app.models.expense  import Expense
        from app.models.wellness import WellnessLog
        from sqlalchemy import func

        ctx         = cls.__new__(cls)
        ctx.user    = user
        ctx.today   = date.today()
        ctx.today_14 = ctx.today - timedelta(days=14)
        ctx.today_60 = ctx.today - timedelta(days=60)

        # ── Tasks ──────────────────────────────────────────────────────────────
        # Single query, load everything for this user
        all_tasks = Task.query.filter_by(user_id=user.id).all()
        ctx.tasks_all    = all_tasks
        ctx.tasks_active = [t for t in all_tasks if not t.completed]
        ctx.tasks_done   = [t for t in all_tasks if t.completed]

        # Completions by calendar day (last 60 days) — one pass, no DB loop
        done_by_day: dict[date, int] = defaultdict(int)
        for t in ctx.tasks_done:
            if t.completed_at:
                d = t.completed_at.date() if isinstance(t.completed_at, datetime) else t.completed_at
                if d >= ctx.today_60:
                    done_by_day[d] += 1
        ctx.tasks_done_by_day = dict(done_by_day)

        # ── Habits ─────────────────────────────────────────────────────────────
        ctx.habits = Habit.query.filter_by(user_id=user.id).all()

        # Habit logs last 60 days — one query, group by date in Python
        if ctx.habits:
            habit_ids = [h.id for h in ctx.habits]
            logs_60 = HabitLog.query.filter(
                HabitLog.habit_id.in_(habit_ids),
                HabitLog.date_logged >= ctx.today_60,
            ).all()
        else:
            logs_60 = []
        ctx.habit_logs_60 = logs_60

        # Logs by day (count across all habits)
        logs_by_day: dict[date, int] = defaultdict(int)
        for log in logs_60:
            logs_by_day[log.date_logged] += 1
        ctx.habit_logs_by_day = dict(logs_by_day)

        # Max streak (single aggregate query)
        ctx.max_streak = (
            db.session.query(func.max(Habit.streak))
            .filter_by(user_id=user.id).scalar() or 0
        )

        # Habit logs in last 30 days for consistency %
        ctx.total_habit_logs_30 = sum(
            1 for log in logs_60
            if log.date_logged >= ctx.today - timedelta(days=30)
        )

        # ── Expenses ──────────────────────────────────────────────────────────
        ctx.expenses_60 = Expense.query.filter(
            Expense.user_id == user.id,
            Expense.date >= ctx.today_60,
        ).all()

        # Spend by day and category totals — one pass
        exp_by_day: dict[date, float]  = defaultdict(float)
        cat_totals: dict[str, float]   = defaultdict(float)
        for e in ctx.expenses_60:
            exp_by_day[e.date] += e.amount
            cat_totals[e.category] += e.amount
        ctx.expense_by_day = dict(exp_by_day)
        ctx.cat_totals     = dict(cat_totals)

        # ── Wellness ───────────────────────────────────────────────────────────
        ctx.wellness_60 = WellnessLog.query.filter(
            WellnessLog.user_id == user.id,
            WellnessLog.date >= ctx.today_60,
        ).order_by(WellnessLog.date.asc()).all()

        # Wellness by date for correlation lookups
        ctx.wellness_by_date = {
            w.date: (w.energy, w.clarity, w.mood)
            for w in ctx.wellness_60
        }

        # ── Achievements ───────────────────────────────────────────────────────
        ctx.achievements_unlocked = {
            ua.achievement.key for ua in user.achievements
        }

        return ctx

    # ── Convenience helpers ────────────────────────────────────────────────────

    def done_in_range(self, start: date, end: date) -> int:
        return sum(
            v for d, v in self.tasks_done_by_day.items()
            if start <= d <= end
        )

    def syncs_in_range(self, start: date, end: date) -> int:
        return sum(
            v for d, v in self.habit_logs_by_day.items()
            if start <= d <= end
        )

    def synced_today(self) -> int:
        return sum(1 for h in self.habits if h.is_synced_today())

    def overdue_count(self) -> int:
        today = self.today
        return sum(
            1 for t in self.tasks_active
            if t.due_date and t.due_date < today
        )

    def critical_count(self) -> int:
        return sum(1 for t in self.tasks_active if t.priority == 'CRITICAL')

    def done_today_count(self) -> int:
        return self.tasks_done_by_day.get(self.today, 0)

    def due_today_count(self) -> int:
        return sum(
            1 for t in self.tasks_active
            if t.due_date == self.today
        )

    def this_week_tasks(self) -> int:
        start = self.today - timedelta(days=6)
        return self.done_in_range(start, self.today)

    def last_week_tasks(self) -> int:
        end   = self.today - timedelta(days=7)
        start = self.today - timedelta(days=13)
        return self.done_in_range(start, end)

    def this_week_syncs(self) -> int:
        start = self.today - timedelta(days=6)
        return self.syncs_in_range(start, self.today)

    def last_week_syncs(self) -> int:
        end   = self.today - timedelta(days=7)
        start = self.today - timedelta(days=13)
        return self.syncs_in_range(start, end)

    def recent_wellness(self, n: int = 7) -> list:
        return self.wellness_60[-n:] if self.wellness_60 else []

    def month_spend(self) -> float:
        start = self.today.replace(day=1)
        return sum(e.amount for e in self.expenses_60 if e.date >= start)

    def at_risk_habits(self) -> list:
        yesterday = self.today - timedelta(days=1)
        return [
            h for h in self.habits
            if h.streak > 0
            and not h.is_synced_today()
            and h.last_completed != yesterday
        ][:3]

    def weekly_syncs_array(self) -> list[int]:
        """7 daily counts, oldest first."""
        return [
            self.habit_logs_by_day.get(self.today - timedelta(days=i), 0)
            for i in range(6, -1, -1)
        ]

    def weekly_labels(self) -> list[str]:
        return [
            (self.today - timedelta(days=i)).strftime('%a')
            for i in range(6, -1, -1)
        ]

    def weekly_done_array(self) -> list[int]:
        return [
            self.tasks_done_by_day.get(self.today - timedelta(days=i), 0)
            for i in range(6, -1, -1)
        ]

    def top_categories(self, n: int = 6) -> tuple[list, list]:
        sorted_cats = sorted(self.cat_totals.items(), key=lambda x: -x[1])[:n]
        labels = [r[0] for r in sorted_cats]
        values = [round(r[1], 2) for r in sorted_cats]
        return labels, values
