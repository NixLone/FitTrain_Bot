from datetime import timedelta

from aiogram import Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Reminder, User, WorkoutLog
from app.keyboards.menu_v2 import get_main_menu
from app.texts.messages_v2 import TODAY_EMPTY_TEXT
from app.utils.dt import format_moscow_time, utc_now

router = Router()


@router.message(lambda m: m.text == "Что сегодня")
async def show_today(message: Message, session: AsyncSession) -> None:
    user = (await session.execute(select(User).where(User.telegram_id == message.from_user.id))).scalar_one_or_none()
    if not user:
        await message.answer("Сначала нажми /start", reply_markup=get_main_menu())
        return

    now = utc_now()
    end_of_day = now + timedelta(days=1)

    reminders_result = await session.execute(
        select(Reminder)
        .options(selectinload(Reminder.workout_type))
        .where(
            Reminder.user_id == user.id,
            Reminder.is_active.is_(True),
            Reminder.next_run_at.is_not(None),
            Reminder.next_run_at >= now,
            Reminder.next_run_at < end_of_day,
        )
        .order_by(Reminder.next_run_at.asc())
    )
    reminders = reminders_result.scalars().all()

    count_done = (
        await session.execute(
            select(WorkoutLog).where(
                WorkoutLog.user_id == user.id,
                WorkoutLog.status == "completed",
                WorkoutLog.performed_at >= now - timedelta(days=1),
            )
        )
    ).scalars().all()

    if not reminders:
        text = TODAY_EMPTY_TEXT + f"\n\nСегодня выполнено тренировок: <b>{len(count_done)}</b>"
        await message.answer(text, reply_markup=get_main_menu())
        return

    lines = ["<b>Что сегодня</b> 🗓", ""]
    for item in reminders:
        lines.append(f"• {format_moscow_time(item.next_run_at)} — <b>{item.workout_type.name}</b>")
    lines.append("")
    lines.append(f"Сегодня уже выполнено: <b>{len(count_done)}</b>")
    await message.answer("\n".join(lines), reply_markup=get_main_menu())
