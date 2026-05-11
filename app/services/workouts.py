from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import WorkoutLog


async def create_manual_workout_log(
    session: AsyncSession,
    *,
    user_id: int,
    workout_type_id: int,
    performed_at: datetime,
    duration_minutes: int | None,
    mood: str | None,
    comment: str | None,
) -> WorkoutLog:
    log = WorkoutLog(
        user_id=user_id,
        workout_type_id=workout_type_id,
        performed_at=performed_at,
        duration_minutes=duration_minutes,
        mood=mood,
        comment=comment,
        status="completed",
        source="manual",
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log
