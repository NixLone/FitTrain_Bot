from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        await session.commit()
        await session.refresh(user)
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        timezone="Europe/Moscow",
        tone="friendly",
        weekly_goal=3,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_tg_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def ensure_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> User:
    user = await get_user_by_tg_id(session, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        await session.commit()
        await session.refresh(user)
        return user

    return await get_or_create_user(
        session,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )


async def update_user_profile(
    session: AsyncSession,
    user: User,
    *,
    height_cm: int | None = None,
    current_weight_kg: float | None = None,
    weekly_goal: int | None = None,
) -> User:
    if height_cm is not None:
        user.height_cm = height_cm
    if current_weight_kg is not None:
        user.current_weight_kg = current_weight_kg
    if weekly_goal is not None:
        user.weekly_goal = weekly_goal

    await session.commit()
    await session.refresh(user)
    return user
