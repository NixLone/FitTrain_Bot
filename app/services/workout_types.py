from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import WorkoutType


async def list_available_workout_types(session: AsyncSession, user_id: int) -> list[WorkoutType]:
    result = await session.execute(
        select(WorkoutType)
        .where(
            WorkoutType.is_active.is_(True),
            or_(WorkoutType.user_id.is_(None), WorkoutType.user_id == user_id),
        )
        .order_by(WorkoutType.is_default.desc(), WorkoutType.name.asc())
    )
    return list(result.scalars().all())


async def create_custom_workout_type(session: AsyncSession, user_id: int, name: str) -> WorkoutType:
    item = WorkoutType(user_id=user_id, name=name.strip(), is_default=False, is_active=True)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item
