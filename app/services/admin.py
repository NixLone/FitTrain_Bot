from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Reminder, User, WorkoutLog
from app.utils.dt import utc_now


async def get_admin_dashboard(session: AsyncSession) -> dict:
    week_start = utc_now() - timedelta(days=7)

    users_count = int((await session.execute(select(func.count(User.id)))).scalar_one() or 0)
    active_reminders = int(
        (
            await session.execute(
                select(func.count(Reminder.id)).where(Reminder.is_active.is_(True))
            )
        ).scalar_one()
        or 0
    )
    workouts_week = int(
        (
            await session.execute(
                select(func.count(WorkoutLog.id)).where(WorkoutLog.performed_at >= week_start)
            )
        ).scalar_one()
        or 0
    )
    new_users_week = int(
        (
            await session.execute(
                select(func.count(User.id)).where(User.created_at >= week_start)
            )
        ).scalar_one()
        or 0
    )

    recent_users_result = await session.execute(
        select(User).order_by(User.created_at.desc()).limit(5)
    )

    return {
        "users_count": users_count,
        "active_reminders": active_reminders,
        "workouts_week": workouts_week,
        "new_users_week": new_users_week,
        "recent_users": list(recent_users_result.scalars().all()),
    }
