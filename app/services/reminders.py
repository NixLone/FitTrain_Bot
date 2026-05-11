from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Reminder, ReminderEvent, ReminderWeekday, WorkoutLog
from app.utils.dt import (
    format_moscow_dt,
    next_interval_run,
    next_one_time_run,
    next_weekly_run,
    utc_now,
)


async def create_reminder(
    session: AsyncSession,
    *,
    user_id: int,
    workout_type_id: int,
    title: str,
    message_text: str,
    schedule_type: str,
    weekdays: list[int] | None = None,
    specific_date_local: datetime | None = None,
    interval_days: int | None = None,
    remind_time=None,
) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        workout_type_id=workout_type_id,
        title=title,
        message_text=message_text,
        schedule_type=schedule_type,
        remind_time=remind_time,
        interval_days=interval_days,
        specific_date=next_one_time_run(specific_date_local) if specific_date_local else None,
        is_active=True,
    )

    if schedule_type == "weekly" and weekdays and remind_time:
        reminder.next_run_at = next_weekly_run(weekdays, remind_time)
    elif schedule_type == "interval" and interval_days and remind_time:
        reminder.next_run_at = next_interval_run(interval_days, remind_time)
    elif schedule_type == "one_time" and specific_date_local:
        reminder.next_run_at = next_one_time_run(specific_date_local)

    session.add(reminder)
    await session.flush()

    if schedule_type == "weekly" and weekdays:
        for wd in weekdays:
            session.add(ReminderWeekday(reminder_id=reminder.id, weekday=wd))

    await session.commit()
    result = await session.execute(
        select(Reminder)
        .options(selectinload(Reminder.workout_type), selectinload(Reminder.weekdays))
        .where(Reminder.id == reminder.id)
    )
    return result.scalar_one()


async def list_user_reminders(session: AsyncSession, user_id: int) -> list[Reminder]:
    result = await session.execute(
        select(Reminder)
        .options(selectinload(Reminder.workout_type), selectinload(Reminder.weekdays))
        .where(Reminder.user_id == user_id, Reminder.is_active.is_(True))
        .order_by(Reminder.created_at.desc())
    )
    return list(result.scalars().all())


async def get_due_reminders(session: AsyncSession) -> list[Reminder]:
    result = await session.execute(
        select(Reminder)
        .options(
            selectinload(Reminder.user),
            selectinload(Reminder.workout_type),
            selectinload(Reminder.weekdays),
        )
        .where(
            Reminder.is_active.is_(True),
            Reminder.next_run_at.is_not(None),
            Reminder.next_run_at <= utc_now(),
        )
    )
    return list(result.scalars().unique().all())


async def create_reminder_event(session: AsyncSession, reminder: Reminder) -> ReminderEvent:
    event = ReminderEvent(
        reminder_id=reminder.id,
        user_id=reminder.user_id,
        workout_type_id=reminder.workout_type_id,
        scheduled_for=reminder.next_run_at,
        sent_at=utc_now(),
        status="sent",
    )
    session.add(event)
    reminder.last_run_at = utc_now()
    reminder.next_run_at = calculate_next_run(reminder)
    await session.commit()
    result = await session.execute(
        select(ReminderEvent)
        .options(
            selectinload(ReminderEvent.reminder).selectinload(Reminder.workout_type),
            selectinload(ReminderEvent.reminder).selectinload(Reminder.user),
        )
        .where(ReminderEvent.id == event.id)
    )
    return result.scalar_one()


async def get_events_due_now(session: AsyncSession) -> list[ReminderEvent]:
    result = await session.execute(
        select(ReminderEvent)
        .options(
            selectinload(ReminderEvent.reminder).selectinload(Reminder.workout_type),
            selectinload(ReminderEvent.reminder).selectinload(Reminder.user),
        )
        .where(ReminderEvent.status == "pending", ReminderEvent.scheduled_for <= utc_now())
    )
    return list(result.scalars().unique().all())


async def send_pending_event(session: AsyncSession, event: ReminderEvent) -> None:
    event.status = "sent"
    event.sent_at = utc_now()
    await session.commit()


async def get_pending_followups(session: AsyncSession, delay_minutes: int) -> list[ReminderEvent]:
    threshold = utc_now() - timedelta(minutes=delay_minutes)
    result = await session.execute(
        select(ReminderEvent)
        .options(
            selectinload(ReminderEvent.reminder).selectinload(Reminder.workout_type),
            selectinload(ReminderEvent.reminder).selectinload(Reminder.user),
        )
        .where(
            ReminderEvent.status == "sent",
            ReminderEvent.sent_at.is_not(None),
            ReminderEvent.sent_at <= threshold,
            ReminderEvent.followup_sent_at.is_(None),
        )
    )
    return list(result.scalars().unique().all())


async def mark_followup_sent(session: AsyncSession, event: ReminderEvent) -> None:
    event.followup_sent_at = utc_now()
    await session.commit()


async def get_evening_check_candidates(session: AsyncSession) -> list[ReminderEvent]:
    result = await session.execute(
        select(ReminderEvent)
        .options(
            selectinload(ReminderEvent.reminder).selectinload(Reminder.workout_type),
            selectinload(ReminderEvent.reminder).selectinload(Reminder.user),
        )
        .where(ReminderEvent.status == "sent", ReminderEvent.evening_check_sent_at.is_(None))
    )
    return list(result.scalars().unique().all())


async def mark_evening_check_sent(session: AsyncSession, event: ReminderEvent) -> None:
    event.evening_check_sent_at = utc_now()
    await session.commit()


async def get_event(session: AsyncSession, event_id: int) -> ReminderEvent | None:
    result = await session.execute(
        select(ReminderEvent)
        .options(
            selectinload(ReminderEvent.reminder).selectinload(Reminder.workout_type),
            selectinload(ReminderEvent.reminder).selectinload(Reminder.user),
        )
        .where(ReminderEvent.id == event_id)
    )
    return result.scalar_one_or_none()


async def complete_event(
    session: AsyncSession,
    *,
    event: ReminderEvent,
    performed_at: datetime,
    duration_minutes: int | None,
    mood: str | None,
    comment: str | None,
    source: str = "reminder",
) -> WorkoutLog:
    event.status = "completed"
    event.response_at = utc_now()
    log = WorkoutLog(
        user_id=event.user_id,
        reminder_event_id=event.id,
        workout_type_id=event.workout_type_id,
        status="completed",
        performed_at=performed_at,
        duration_minutes=duration_minutes,
        mood=mood,
        comment=comment,
        source=source,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def skip_event(session: AsyncSession, *, event: ReminderEvent, reason: str | None) -> WorkoutLog:
    event.status = "skipped"
    event.response_at = utc_now()
    log = WorkoutLog(
        user_id=event.user_id,
        reminder_event_id=event.id,
        workout_type_id=event.workout_type_id,
        status="skipped",
        performed_at=utc_now(),
        skip_reason=reason,
        source="reminder",
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def reschedule_event(
    session: AsyncSession,
    *,
    event: ReminderEvent,
    new_dt_local: datetime,
) -> WorkoutLog:
    from app.utils.dt import moscow_to_utc

    event.status = "snoozed"
    event.response_at = utc_now()
    new_event = ReminderEvent(
        reminder_id=event.reminder_id,
        user_id=event.user_id,
        workout_type_id=event.workout_type_id,
        scheduled_for=moscow_to_utc(new_dt_local),
        status="pending",
    )
    session.add(new_event)
    log = WorkoutLog(
        user_id=event.user_id,
        reminder_event_id=event.id,
        workout_type_id=event.workout_type_id,
        status="rescheduled",
        performed_at=utc_now(),
        rescheduled_to=moscow_to_utc(new_dt_local),
        source="reminder",
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log



def calculate_next_run(reminder: Reminder):
    if reminder.schedule_type == "weekly":
        weekdays = [item.weekday for item in reminder.weekdays]
        if reminder.remind_time and weekdays:
            return next_weekly_run(weekdays, reminder.remind_time)
    elif reminder.schedule_type == "interval":
        if reminder.interval_days and reminder.remind_time:
            return next_interval_run(reminder.interval_days, reminder.remind_time, utc_now())
    elif reminder.schedule_type == "one_time":
        reminder.is_active = False
        return None
    return None



def render_reminder_line(reminder: Reminder) -> str:
    next_part = format_moscow_dt(reminder.next_run_at) if reminder.next_run_at else "не рассчитано"
    return f"• <b>{reminder.title}</b> — {reminder.workout_type.name} — {next_part}"
