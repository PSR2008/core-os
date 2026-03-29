"""
app/services/feedback_service.py — Emotional feedback messages.

Generates adaptive, data-driven messages shown as banners on the dashboard.
Messages respond to real events: streak milestones, weekly improvements,
activity drops, and first-time actions.

Returns a list of up to 2 banners, each with: { text, type, icon }.
Type: 'celebration' | 'encouragement' | 'warning' | 'milestone'
"""
from __future__ import annotations
from datetime import date, timedelta


def get_feedback_banners(user, t_data: dict, h_data: dict, w_data: dict) -> list[dict]:
    """
    Evaluate feedback conditions for the current user state.
    Returns at most 2 banners ordered by emotional impact.
    """
    banners = []

    # ── Streak milestones ──────────────────────────────────────────────────────
    streak = user.login_streak
    if streak in (3, 7, 14, 30, 60, 100):
        labels = {
            3:   ('3-day streak unlocked', 'The habit of showing up is starting.'),
            7:   ('7-day streak — Week Warrior!', 'One full week of consistency. This is how operatives are built.'),
            14:  ('14-day streak — Iron Discipline', 'Two weeks straight. You\'re in the top tier of users.'),
            30:  ('30-day streak — Elite Operative!', 'A full month. Most people never get here. You\'re not most people.'),
            60:  ('60-day streak — Legendary', 'Two months of unbroken commitment. You\'ve built a real system.'),
            100: ('100-day streak — Immortal Operative', 'One hundred days. This is identity, not habit.'),
        }
        title, body = labels[streak]
        banners.append(dict(
            icon='🔥', type='milestone',
            text=f'{title}: {body}',
        ))

    # ── Top habit streak milestone ─────────────────────────────────────────────
    top_streak = h_data.get('top_streak', 0)
    if top_streak in (7, 14, 21, 30) and h_data.get('synced_today', 0) > 0:
        banners.append(dict(
            icon='🏆', type='celebration',
            text=f'{top_streak}-day habit streak! Your consistency is in the top percentile.',
        ))

    # ── Weekly improvement ─────────────────────────────────────────────────────
    this_week = t_data.get('this_week', 0)
    last_week = t_data.get('last_week', 0)
    if last_week > 0 and this_week > last_week:
        pct = round((this_week - last_week) / last_week * 100)
        if pct >= 50:
            banners.append(dict(
                icon='📈', type='celebration',
                text=f'You improved {pct}% this week — {this_week} tasks vs {last_week} last week. Keep this energy.',
            ))
        elif pct >= 25:
            banners.append(dict(
                icon='⬆️', type='encouragement',
                text=f'Up {pct}% this week. Small improvements compound into major progress.',
            ))

    # ── Activity drop: was active, now quiet ──────────────────────────────────
    if last_week >= 3 and this_week == 0 and date.today().weekday() >= 2:
        # Mid-week and nothing done yet this week, but last week was active
        banners.append(dict(
            icon='💡', type='encouragement',
            text=f'You completed {last_week} tasks last week. This week is still yours — one task now breaks the pause.',
        ))

    # ── Wellness bounce ────────────────────────────────────────────────────────
    if w_data.get('has_data') and w_data.get('trend') == 'up':
        avg = w_data.get('overall_avg', 0)
        if avg >= 7.5:
            banners.append(dict(
                icon='✨', type='encouragement',
                text=f'Wellness up to {avg}/10 — high biometric scores correlate with your best task days.',
            ))

    # ── All habits synced today ────────────────────────────────────────────────
    total_h  = h_data.get('total', 0)
    synced_h = h_data.get('synced_today', 0)
    if total_h >= 2 and synced_h == total_h:
        banners.append(dict(
            icon='⚡', type='celebration',
            text=f'All {total_h} habits synced today. Full sync achieved — bonus XP and CR earned.',
        ))

    # ── Level up message ──────────────────────────────────────────────────────
    # Show when XP is within 5 of a level boundary (user just levelled up)
    xp_mod = user.total_xp % 100
    if xp_mod <= 5 and user.level > 1:
        banners.append(dict(
            icon='🎖️', type='milestone',
            text=f'Level {user.level} reached — {user.total_xp} XP total. Each level compounds your capabilities.',
        ))

    # Return max 2, prioritise milestones
    ordered = sorted(banners, key=lambda b: (
        0 if b['type'] == 'milestone'    else
        1 if b['type'] == 'celebration'  else
        2 if b['type'] == 'encouragement' else 3
    ))
    return ordered[:2]
