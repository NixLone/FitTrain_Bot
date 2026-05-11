from datetime import timedelta

from aiogram import Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Reminder, WorkoutLog
from app.keyboards.menu_v2 import get_main_menu
from app.services.plans_smart import get_active_plan, render_today_plan
from app.services.users import ensure_user
from app.texts.messages_v2 import TODAY_EMPTY_TEXT
from app.utils.dt import format_moscow_time, utc_now

router = Router()


@router.message(lambda m: m.text == "Что сегодня")
async def show_today(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    user = await ensure_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )

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

    lines = ["<b>Что сегодня</b>", ""]
    if reminders:
        for item in reminders:
            lines.append(f"• {format_moscow_time(item.next_run_at)} — <b>{item.workout_type.name}</b>")
    else:
        lines.append(TODAY_EMPTY_TEXT)

    lines.append("")
    lines.append(f"Сегодня выполнено: <b>{len(count_done)}</b>")

    plan = await get_active_plan(session, user.id)
    plan_text = render_today_plan(plan)
    if plan_text:
        lines.append("")
        lines.append(plan_text)

    await message.answer("\n".join(lines), reply_markup=get_main_menu(message.from_user.id))
