from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import get_settings

settings = get_settings()
MOSCOW_TZ = ZoneInfo(settings.bot_timezone)
UTC = timezone.utc

WEEKDAY_MAP = {
    1: "Пн",
    2: "Вт",
    3: "Ср",
    4: "Чт",
    5: "Пт",
    6: "Сб",
    7: "Вс",
}


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def moscow_now() -> datetime:
    return datetime.now(MOSCOW_TZ)


def utc_to_moscow(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(MOSCOW_TZ)


def moscow_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MOSCOW_TZ)
    return dt.astimezone(UTC).replace(tzinfo=None)


def parse_time_hhmm(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("Неверный формат времени")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Неверное время")
    return time(hour=hour, minute=minute)


def parse_date_ddmmyyyy(value: str) -> date:
    day, month, year = value.strip().split(".")
    return date(year=int(year), month=int(month), day=int(day))


def parse_datetime_ddmmyyyy_hhmm(value: str) -> datetime:
    date_part, time_part = value.strip().split()
    d = parse_date_ddmmyyyy(date_part)
    t = parse_time_hhmm(time_part)
    return datetime.combine(d, t, tzinfo=MOSCOW_TZ)


def format_moscow_dt(dt: datetime) -> str:
    local_dt = utc_to_moscow(dt)
    return local_dt.strftime("%d.%m.%Y %H:%M")


def format_moscow_time(dt: datetime) -> str:
    return utc_to_moscow(dt).strftime("%H:%M")


def next_weekly_run(weekdays: list[int], remind_time: time) -> datetime:
    now_local = moscow_now()
    today = now_local.date()
    current_wd = now_local.isoweekday()
    candidates: list[datetime] = []

    for wd in weekdays:
        days_ahead = (wd - current_wd) % 7
        target_date = today + timedelta(days=days_ahead)
        candidate = datetime.combine(target_date, remind_time, tzinfo=MOSCOW_TZ)
        if candidate <= now_local:
            candidate += timedelta(days=7)
        candidates.append(candidate)

    return moscow_to_utc(min(candidates))


def next_interval_run(interval_days: int, remind_time: time, last_base: datetime | None = None) -> datetime:
    base_local = utc_to_moscow(last_base) if last_base else moscow_now()
    target_date = (base_local + timedelta(days=interval_days)).date()
    target = datetime.combine(target_date, remind_time, tzinfo=MOSCOW_TZ)
    return moscow_to_utc(target)


def next_one_time_run(specific_dt_local: datetime) -> datetime:
    return moscow_to_utc(specific_dt_local)
