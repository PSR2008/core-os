"""
app/models/__init__.py — Re-export all models so Flask-Migrate
can discover them and generate correct migration scripts.
"""
from app.models.user        import User        # noqa: F401
from app.models.task        import Task        # noqa: F401
from app.models.habit       import Habit, HabitLog  # noqa: F401
from app.models.expense     import Expense     # noqa: F401
from app.models.wellness    import WellnessLog # noqa: F401
from app.models.shop        import ShopItem, UserInventory  # noqa: F401
from app.models.achievement import Achievement, UserAchievement  # noqa: F401

from app.models.feedback import UserFeedback  # noqa: F401
from app.models.growth   import GrowthEvent   # noqa: F401
