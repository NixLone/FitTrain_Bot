from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Reminder


async def get_suggested_hours(session: AsyncSession, user_id: int) -> list[int]:
    defaults = [10, 12, 14, 16, 18]
    result = await session.execute(
        select(func.strftime("%H", Reminder.remind_time).label("hour"), func.count(Reminder.id).label("cnt"))
        .where(
            Reminder.user_id == user_id,
            Reminder.is_active.is_(True),
            Reminder.remind_time.is_not(None),
        )
        .group_by("hour")
        .order_by(func.count(Reminder.id).desc())
        .limit(5)
    )
    values: list[int] = []
    for row in result.all():
        if row.hour is not None:
            values.append(int(row.hour))
    for hour in defaults:
        if hour not in values:
            values.append(hour)
    return values[:5]
