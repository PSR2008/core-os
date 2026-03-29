"""
app/services/achievement_service.py — Achievements with DataContext support.

check_and_unlock still writes to DB (it must — it creates new rows).
get_progress_hints now accepts ctx for zero-query hint generation.
"""
from app.extensions import db

ACHIEVEMENT_DEFS = [
    # Bronze
    dict(key='first_task',      name='First Strike',       icon='⚡', xp_reward=25,  tier='bronze', description='Complete your very first task.'),
    dict(key='first_habit',     name='Routine Init',       icon='🔄', xp_reward=25,  tier='bronze', description='Sync a habit for the first time.'),
    dict(key='first_purchase',  name='First Acquisition',  icon='🛒', xp_reward=30,  tier='bronze', description='Buy your first shop upgrade.'),
    dict(key='streak_3',        name='Three-Peat',         icon='🔥', xp_reward=30,  tier='bronze', description='Reach a 3-day streak on any habit.'),
    dict(key='zero_overdue',    name='Clean Slate',        icon='✨', xp_reward=50,  tier='bronze', description='Have zero overdue tasks.'),
    # Silver
    dict(key='task_10',         name='Task Decimator',     icon='💥', xp_reward=50,  tier='silver', description='Complete 10 tasks total.'),
    dict(key='streak_7',        name='Week Warrior',       icon='🗓️', xp_reward=75,  tier='silver', description='Reach a 7-day streak on any habit.'),
    dict(key='level_5',         name='Operative Lv.5',     icon='🎖️', xp_reward=100, tier='silver', description='Reach Level 5.'),
    dict(key='all_synced',      name='Full Sync',          icon='📡', xp_reward=40,  tier='silver', description='Sync all habits on the same day.'),
    dict(key='budget_keeper',   name='Budget Keeper',      icon='💰', xp_reward=50,  tier='silver', description='Stay within budget.'),
    dict(key='wellness_week',   name='Biometric Streak',   icon='💊', xp_reward=75,  tier='silver', description='Log wellness 7 days in a row.'),
    dict(key='collector',       name='Collector',          icon='📦', xp_reward=100, tier='silver', description='Own 5+ shop upgrades.'),
    # Gold
    dict(key='task_50',         name='Task Machine',       icon='🤖', xp_reward=150, tier='gold',   description='Complete 50 tasks total.'),
    dict(key='task_100',        name='Centurion',          icon='🎯', xp_reward=300, tier='gold',   description='Complete 100 tasks total.'),
    dict(key='streak_30',       name='Iron Discipline',    icon='🏋️', xp_reward=200, tier='gold',   description='Reach a 30-day streak on any habit.'),
    dict(key='level_10',        name='Operative Lv.10',    icon='🌟', xp_reward=250, tier='gold',   description='Reach Level 10.'),
    dict(key='level_20',        name='Elite Operative',    icon='💎', xp_reward=500, tier='gold',   description='Reach Level 20.'),
    dict(key='wellness_perfect', name='Peak State',        icon='🧬', xp_reward=100, tier='gold',   description='Log energy, clarity, and mood all 9+ in one session.'),
    dict(key='threat_zero',     name='Zero Threat',        icon='🛡️', xp_reward=100, tier='gold',   description='Achieve a threat score of 0.'),
]


def seed_achievements() -> None:
    from app.models.achievement import Achievement
    for a in ACHIEVEMENT_DEFS:
        existing = Achievement.query.filter_by(key=a['key']).first()
        if not existing:
            db.session.add(Achievement(**a))
        else:
            existing.tier = a['tier']
    db.session.commit()


def check_and_unlock(user, ctx=None) -> list:
    """
    Evaluate achievements. Uses ctx for efficiency where possible.
    Still writes to DB when new achievements are unlocked.
    """
    from datetime import date, timedelta
    from app.models.achievement import Achievement, UserAchievement
    from app.models.wellness     import WellnessLog
    from app.services.game_service import compute_threat_score

    already        = {ua.achievement.key for ua in user.achievements}
    newly_unlocked = []

    def unlock(key: str) -> None:
        if key in already: return
        a = Achievement.query.filter_by(key=key).first()
        if not a: return
        db.session.add(UserAchievement(user_id=user.id, achievement_id=a.id))
        user.total_xp += a.xp_reward
        already.add(key)
        newly_unlocked.append(a)

    # Use DataContext pre-loaded data when available; fall back to direct DB queries
    if ctx is not None:
        tasks_done = len(ctx.tasks_done)
        overdue    = ctx.overdue_count()
        max_streak = ctx.max_streak
        habits     = ctx.habits
    else:
        from app.models.task  import Task
        from app.models.habit import Habit
        from datetime import date as _date
        tasks_done = Task.query.filter_by(user_id=user.id, completed=True).count()
        overdue    = Task.query.filter(
            Task.user_id == user.id, Task.completed == False,
            Task.due_date < _date.today(), Task.due_date.isnot(None)).count()
        max_streak = db.session.query(db.func.max(Habit.streak)).filter_by(user_id=user.id).scalar() or 0
        habits     = Habit.query.filter_by(user_id=user.id).all()

    if tasks_done >= 1:   unlock('first_task')
    if tasks_done >= 10:  unlock('task_10')
    if tasks_done >= 50:  unlock('task_50')
    if tasks_done >= 100: unlock('task_100')
    if overdue == 0 and tasks_done > 0: unlock('zero_overdue')

    # Habit logs — need a DB call here regardless
    from app.models.habit    import HabitLog, Habit as _Habit
    from app.models.wellness import WellnessLog as _WL

    total_logs = (
        len(ctx.habit_logs_60) if ctx else
        HabitLog.query.join(HabitLog.habit).filter_by(user_id=user.id).count()
    )
    if total_logs >= 1: unlock('first_habit')
    if max_streak >= 3:  unlock('streak_3')
    if max_streak >= 7:  unlock('streak_7')
    if max_streak >= 30: unlock('streak_30')
    if habits and all(h.is_synced_today() for h in habits): unlock('all_synced')

    if user.level >= 5:  unlock('level_5')
    if user.level >= 10: unlock('level_10')
    if user.level >= 20: unlock('level_20')

    inv_count = user.inventory.count()
    if inv_count >= 1: unlock('first_purchase')
    if inv_count >= 5: unlock('collector')

    # Wellness streak — still needs ordered date list
    today = date.today()
    w_logs = (
        sorted([l for l in ctx.wellness_60 if l.date >= today - timedelta(days=7)], key=lambda l: l.date)
        if ctx else
        _WL.query.filter_by(user_id=user.id).order_by(_WL.date.desc()).limit(7).all()
    )
    if len(w_logs) == 7:
        expected = [(today - timedelta(days=i)) for i in range(7)]
        if sorted([l.date for l in w_logs], reverse=True) == expected:
            unlock('wellness_week')

    latest_w = w_logs[-1] if w_logs else None
    if latest_w and latest_w.energy >= 9 and latest_w.clarity >= 9 and latest_w.mood >= 9:
        unlock('wellness_perfect')

    if user.budget > 0 and user.spent <= user.budget: unlock('budget_keeper')

    threat = compute_threat_score(user, ctx)
    if threat['score'] == 0 and tasks_done > 0: unlock('threat_zero')

    if newly_unlocked:
        db.session.commit()
    return newly_unlocked


def get_progress_hints(user, ctx=None) -> list:
    from app.models.achievement import Achievement

    already    = {ua.achievement.key for ua in user.achievements}
    done       = len(ctx.tasks_done) if ctx else 0
    max_streak = ctx.max_streak if ctx else 0

    if not ctx:
        from app.models.task  import Task
        from app.models.habit import Habit
        done       = Task.query.filter_by(user_id=user.id, completed=True).count()
        max_streak = db.session.query(db.func.max(Habit.streak)).filter_by(user_id=user.id).scalar() or 0

    hints = []
    candidates = [
        ('task_10',  done,        10,  f'{done}/10 tasks'),
        ('task_50',  done,        50,  f'{done}/50 tasks'),
        ('task_100', done,        100, f'{done}/100 tasks'),
        ('streak_7', max_streak,  7,   f'{max_streak}/7 day streak'),
        ('streak_30',max_streak,  30,  f'{max_streak}/30 day streak'),
        ('level_5',  user.level,  5,   f'Level {user.level}/5'),
        ('level_10', user.level,  10,  f'Level {user.level}/10'),
        ('level_20', user.level,  20,  f'Level {user.level}/20'),
    ]
    for key, current, target, label in candidates:
        if key in already or current >= target: continue
        pct = round(current / target * 100)
        if pct < 5: continue
        a = Achievement.query.filter_by(key=key).first()
        if not a: continue
        hints.append(dict(
            key=key, icon=a.icon, name=a.name, tier=a.tier,
            tier_color=a.tier_color, description=a.description,
            xp_reward=a.xp_reward, progress_pct=pct, progress_label=label,
        ))
    hints.sort(key=lambda h: -h['progress_pct'])
    return hints[:3]


def get_achievement_summary(user) -> dict:
    from app.models.achievement import Achievement, TIER_COLORS
    unlocked_ids = {ua.achievement_id for ua in user.achievements}
    total_by_tier    = {t: 0 for t in TIER_COLORS}
    unlocked_by_tier = {t: 0 for t in TIER_COLORS}
    for a in Achievement.query.all():
        if a.tier in total_by_tier:
            total_by_tier[a.tier] += 1
            if a.id in unlocked_ids:
                unlocked_by_tier[a.tier] += 1
    return dict(
        total=sum(total_by_tier.values()),
        unlocked=sum(unlocked_by_tier.values()),
        by_tier={
            tier: dict(
                unlocked=unlocked_by_tier[tier], total=total_by_tier[tier],
                color=TIER_COLORS[tier],
                pct=round(unlocked_by_tier[tier] / total_by_tier[tier] * 100)
                    if total_by_tier[tier] else 0,
            )
            for tier in TIER_COLORS
        }
    )
