import asyncio
import logging

from app.bot import create_bot, create_dispatcher
from app.database.session import init_db
from app.services.seed import seed_default_workout_types
from app.services.scheduler import setup_scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    await init_db()
    await seed_default_workout_types()

    bot = create_bot()
    dp = create_dispatcher()

    setup_scheduler(bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
