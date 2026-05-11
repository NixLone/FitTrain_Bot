from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import WorkoutLog, WorkoutType
from app.utils.dt import utc_now


async def get_stats(session: AsyncSession, user_id: int) -> dict:
    week_start = utc_now() - timedelta(days=7)

    total_completed_stmt = select(func.count(WorkoutLog.id)).where(
        WorkoutLog.user_id == user_id,
        WorkoutLog.status == "completed",
    )
    week_completed_stmt = select(func.count(WorkoutLog.id)).where(
        WorkoutLog.user_id == user_id,
        WorkoutLog.status == "completed",
        WorkoutLog.performed_at >= week_start,
    )
    total_completed = int((await session.execute(total_completed_stmt)).scalar_one() or 0)
    week_completed = int((await session.execute(week_completed_stmt)).scalar_one() or 0)

    top_types_stmt = (
        select(WorkoutType.name, func.count(WorkoutLog.id).label("cnt"))
        .join(WorkoutType, WorkoutType.id == WorkoutLog.workout_type_id)
        .where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.status == "completed",
        )
        .group_by(WorkoutType.name)
        .order_by(func.count(WorkoutLog.id).desc())
    )
    top_types = (await session.execute(top_types_stmt)).all()

    all_dates_result = await session.execute(
        select(WorkoutLog.performed_at)
        .where(WorkoutLog.user_id == user_id, WorkoutLog.status == "completed")
        .order_by(WorkoutLog.performed_at.asc())
    )
    all_dates = [row[0] for row in all_dates_result.all()]
    average_gap_days = None
    if len(all_dates) >= 2:
        gaps = []
        for prev, cur in zip(all_dates, all_dates[1:]):
            gaps.append((cur - prev).total_seconds() / 86400)
        average_gap_days = round(sum(gaps) / len(gaps), 1)

    return {
        "total_completed": total_completed,
        "week_completed": week_completed,
        "top_types": top_types,
        "average_gap_days": average_gap_days,
    }
