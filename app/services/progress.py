from __future__ import annotations

from datetime import timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BodyMeasurement, User, WorkoutLog, WorkoutType
from app.utils.dt import utc_now


async def add_weight_measurement(
    session: AsyncSession,
    *,
    user: User,
    weight_kg: float,
    comment: str | None = None,
) -> BodyMeasurement:
    item = BodyMeasurement(user_id=user.id, weight_kg=weight_kg, comment=comment)
    user.current_weight_kg = weight_kg
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def get_latest_measurements(
    session: AsyncSession, user_id: int, limit: int = 5
) -> list[BodyMeasurement]:
    result = await session.execute(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user_id)
        .order_by(desc(BodyMeasurement.measured_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_recent_workouts(
    session: AsyncSession, user_id: int, limit: int = 5
) -> list[tuple[WorkoutLog, str]]:
    result = await session.execute(
        select(WorkoutLog, WorkoutType.name)
        .join(WorkoutType, WorkoutType.id == WorkoutLog.workout_type_id)
        .where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.status == "completed",
        )
        .order_by(desc(WorkoutLog.performed_at))
        .limit(limit)
    )
    return list(result.all())


async def get_progress_summary(session: AsyncSession, user: User) -> dict:
    latest_measurements = await get_latest_measurements(session, user.id, limit=5)
    recent_workouts = await get_recent_workouts(session, user.id, limit=5)

    start_week = utc_now() - timedelta(days=7)

    total_minutes_stmt = select(func.coalesce(func.sum(WorkoutLog.duration_minutes), 0)).where(
        WorkoutLog.user_id == user.id,
        WorkoutLog.status == "completed",
        WorkoutLog.performed_at >= start_week,
    )
    total_minutes = int((await session.execute(total_minutes_stmt)).scalar_one() or 0)

    completed_stmt = select(func.count(WorkoutLog.id)).where(
        WorkoutLog.user_id == user.id,
        WorkoutLog.status == "completed",
        WorkoutLog.performed_at >= start_week,
    )
    completed_week = int((await session.execute(completed_stmt)).scalar_one() or 0)

    first_measurement = latest_measurements[-1] if latest_measurements else None
    latest_measurement = latest_measurements[0] if latest_measurements else None
    delta_weight = None
    if latest_measurement and first_measurement:
        current = latest_measurement.weight_kg
        previous = first_measurement.weight_kg
        if current is not None and previous is not None:
            delta_weight = round(current - previous, 1)

    return {
        "current_weight": user.current_weight_kg,
        "height_cm": user.height_cm,
        "completed_week": completed_week,
        "weekly_goal": user.weekly_goal,
        "total_minutes": total_minutes,
        "delta_weight": delta_weight,
        "first_weight": first_measurement.weight_kg if first_measurement else None,
        "latest_weight": latest_measurement.weight_kg if latest_measurement else None,
        "latest_measurements": latest_measurements,
        "recent_workouts": recent_workouts,
    }
