from sqlalchemy import select

from app.database.models import WorkoutType
from app.database.session import SessionLocal

DEFAULT_TYPES = [
    "Силовая",
    "Кардио",
    "Ноги",
    "Спина",
    "Грудь",
    "Руки",
    "Плечи",
    "Растяжка",
    "Пресс",
    "Домашняя тренировка",
    "Бег",
    "Велосипед",
    "Плавание",
    "Своя тренировка",
]

DEFAULT_TYPES = [
    "Силовая",
    "Кардио",
    "Ноги",
    "Спина",
    "Грудь",
    "Руки",
    "Плечи",
    "Растяжка",
    "Пресс",
    "Домашняя тренировка",
    "Бег",
    "Велосипед",
    "Плавание",
    "Своя тренировка",
    "Групповое занятие",
    "Занятие с тренером",
]


async def seed_default_workout_types() -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(WorkoutType).where(WorkoutType.user_id.is_(None)))
        existing = {row.name for row in result.scalars().all()}
        for name in DEFAULT_TYPES:
            if name not in existing:
                session.add(WorkoutType(name=name, user_id=None, is_default=True, is_active=True))
        await session.commit()
