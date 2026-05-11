from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database.base import Base

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = await conn.exec_driver_sql(f"PRAGMA table_info({table_name})")
    rows = result.fetchall()
    return any(row[1] == column_name for row in rows)


async def _apply_sqlite_migrations(conn) -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    if await _column_exists(conn, "users", "height_cm") is False:
        await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN height_cm INTEGER")

    if await _column_exists(conn, "users", "current_weight_kg") is False:
        await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN current_weight_kg FLOAT")

    if await _column_exists(conn, "workout_logs", "mood") is False:
        await conn.exec_driver_sql("ALTER TABLE workout_logs ADD COLUMN mood VARCHAR(64)")


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _apply_sqlite_migrations(conn)
