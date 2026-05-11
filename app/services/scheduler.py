from datetime import timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.database.session import SessionLocal
from app.keyboards.reminders import reminder_actions_kb
from app.services.reminders import (
    create_reminder_event,
    get_due_reminders,
    get_evening_check_candidates,
    get_events_due_now,
    get_pending_followups,
    mark_evening_check_sent,
    mark_followup_sent,
    send_pending_event,
)
from app.utils.dt import format_moscow_dt, moscow_now, utc_to_moscow

settings = get_settings()
scheduler = AsyncIOScheduler(timezone=settings.bot_timezone)


async def process_due_reminders(bot: Bot) -> None:
    async with SessionLocal() as session:
        reminders = await get_due_reminders(session)
        for reminder in reminders:
            event = await create_reminder_event(session, reminder)
            await bot.send_message(
                chat_id=reminder.user.telegram_id,
                text=(
                    f"Пора заниматься 💪\n\n"
                    f"<b>{reminder.workout_type.name}</b>\n"
                    f"{reminder.message_text}\n"
                    f"Время: {format_moscow_dt(event.scheduled_for)}"
                ),
                reply_markup=reminder_actions_kb(event.id),
            )


async def process_due_event_reschedules(bot: Bot) -> None:
    async with SessionLocal() as session:
        events = await get_events_due_now(session)
        for event in events:
            await send_pending_event(session, event)
            await bot.send_message(
                chat_id=event.reminder.user.telegram_id,
                text=(
                    f"Напоминаю про тренировку 💪\n\n"
                    f"<b>{event.reminder.workout_type.name}</b>\n"
                    f"{event.reminder.message_text}\n"
                    f"Время: {format_moscow_dt(event.scheduled_for)}"
                ),
                reply_markup=reminder_actions_kb(event.id),
            )


async def process_followups(bot: Bot) -> None:
    async with SessionLocal() as session:
        events = await get_pending_followups(session, settings.followup_delay_minutes)
        for event in events:
            await bot.send_message(
                chat_id=event.reminder.user.telegram_id,
                text=(
                    f"Напоминаю про тренировку 💪\n"
                    f"Ты ещё не отметил результат по: <b>{event.reminder.workout_type.name}</b>"
                ),
                reply_markup=reminder_actions_kb(event.id),
            )
            await mark_followup_sent(session, event)


async def process_evening_checks(bot: Bot) -> None:
    now_local = moscow_now()
    if now_local.hour < settings.evening_check_hour:
        return

    async with SessionLocal() as session:
        events = await get_evening_check_candidates(session)
        today = now_local.date()
        for event in events:
            scheduled_local = utc_to_moscow(event.scheduled_for)
            if scheduled_local.date() != today:
                continue
            await bot.send_message(
                chat_id=event.reminder.user.telegram_id,
                text=(
                    f"Как прошла тренировка сегодня?\n"
                    f"<b>{event.reminder.workout_type.name}</b>"
                ),
                reply_markup=reminder_actions_kb(event.id),
            )
            await mark_evening_check_sent(session, event)


def setup_scheduler(bot: Bot) -> None:
    scheduler.add_job(process_due_reminders, "interval", seconds=60, kwargs={"bot": bot}, id="due_reminders", replace_existing=True)
    scheduler.add_job(process_due_event_reschedules, "interval", seconds=60, kwargs={"bot": bot}, id="due_events", replace_existing=True)
    scheduler.add_job(process_followups, "interval", seconds=300, kwargs={"bot": bot}, id="followups", replace_existing=True)
    scheduler.add_job(process_evening_checks, "interval", seconds=900, kwargs={"bot": bot}, id="evening_checks", replace_existing=True)
    scheduler.start()
