from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import get_settings
from app.handlers import admin_v2, analytics_v2, plans_v3, progress_v3, reminders_v3, start_v2, today_v3, workouts_v4
from app.middlewares.db import DbSessionMiddleware
from app.database.session import SessionLocal


def create_bot() -> Bot:
    settings = get_settings()
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    db_middleware = DbSessionMiddleware(SessionLocal)
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)

    dp.include_router(start_v2.router)
    dp.include_router(today_v3.router)
    dp.include_router(workouts_v4.router)
    dp.include_router(reminders_v3.router)
    dp.include_router(plans_v3.router)
    dp.include_router(progress_v3.router)
    dp.include_router(analytics_v2.router)
    dp.include_router(admin_v2.router)
    return dp
