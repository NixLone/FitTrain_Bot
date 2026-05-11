from __future__ import annotations

from collections import defaultdict

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import TrainingPlan, TrainingPlanItem, User, WorkoutLog, WorkoutType
from app.services.workout_types import list_available_workout_types
from app.utils.dt import WEEKDAY_MAP, moscow_now

HEAVY_KEYWORDS = ("сил", "жим", "тяга", "присед", "гири", "штанг", "тренаж", "зал")


def _normalize(value: str) -> str:
    return value.lower().strip()


def _type_bucket(name: str) -> str:
    value = _normalize(name)
    if any(token in value for token in ("растяж", "йога", "мобил")):
        return "mobility"
    if any(token in value for token in ("бег", "кардио", "ходьб", "вел")):
        return "cardio"
    if any(token in value for token in ("тренер", "групп")):
        return "coached"
    if any(token in value for token in HEAVY_KEYWORDS):
        return "strength"
    return "general"


def _format_day_list(days: list[int]) -> str:
    return ", ".join(WEEKDAY_MAP.get(day, str(day)) for day in sorted(days))


def _plan_title_for_type(name: str) -> str:
    bucket = _type_bucket(name)
    if bucket == "strength":
        return f"{name}: основная силовая работа"
    if bucket == "cardio":
        return f"{name}: кардио-сессия"
    if bucket == "mobility":
        return f"{name}: восстановление"
    if bucket == "coached":
        return f"{name}: приоритетная сессия"
    return name


def _plan_description_for_type(name: str, bucket: str, seen_count: int, extra: bool) -> str:
    history_note = (
        "Ты уже часто выбираешь этот формат, поэтому оставляю его как опорную часть недели."
        if seen_count >= 2
        else "Добавил этот формат в план как полезное разнообразие под твои интересы."
    )
    if bucket == "strength":
        base = (
            "Сделай основную работу в том формате, который тебе реально подходит: техника, рабочие подходы,"
            " контроль нагрузки и упражнения, которые ты действительно используешь."
        )
    elif bucket == "cardio":
        base = "Держи ровный темп, без гонки за скоростью. Ориентир — качественная работа на выносливость."
    elif bucket == "mobility":
        base = "Сфокусируйся на подвижности, дыхании и восстановлении, а не на высокой интенсивности."
    elif bucket == "coached":
        base = "Используй сессию для корректировки техники, нагрузки и обратной связи по самочувствию."
    else:
        base = "Собери тренировку вокруг упражнений, которые тебе интересны и хорошо заходят по практике."
    if extra:
        base = "Это дополнительный блок к основному занятию. " + base
    return f"{base} {history_note}"


def _intensity_for_bucket(bucket: str, extra: bool) -> str:
    if bucket == "mobility":
        return "легкая"
    if bucket == "cardio":
        return "умеренная"
    if bucket == "coached":
        return "контролируемая"
    if extra:
        return "поддерживающая"
    return "основная"


async def _get_history_counts(session: AsyncSession, user_id: int) -> dict[int, int]:
    result = await session.execute(
        select(WorkoutLog.workout_type_id, func.count(WorkoutLog.id))
        .where(WorkoutLog.user_id == user_id, WorkoutLog.status == "completed")
        .group_by(WorkoutLog.workout_type_id)
    )
    return {workout_type_id: count for workout_type_id, count in result.all()}


async def get_ranked_workout_types(session: AsyncSession, user_id: int) -> list[WorkoutType]:
    types_ = await list_available_workout_types(session, user_id)
    history_counts = await _get_history_counts(session, user_id)
    return sorted(types_, key=lambda item: (-history_counts.get(item.id, 0), item.name.lower()))


async def generate_plan_for_user(
    session: AsyncSession,
    user: User,
    *,
    selected_days: list[int] | None = None,
    selected_type_ids: list[int] | None = None,
    daily_minutes: int | None = None,
) -> TrainingPlan:
    available_types = await get_ranked_workout_types(session, user.id)
    types_by_id = {item.id: item for item in available_types}
    history_counts = await _get_history_counts(session, user.id)

    chosen_days = sorted(set(selected_days or []))
    if not chosen_days:
        chosen_days = [1, 3, 5][: max(1, min(user.weekly_goal or 3, 3))]

    chosen_type_ids = [type_id for type_id in (selected_type_ids or []) if type_id in types_by_id]
    if not chosen_type_ids:
        chosen_type_ids = [item.id for item in available_types[: max(1, min(len(available_types), 3))]]

    minutes_limit = daily_minutes or 60
    selected_types = [types_by_id[type_id] for type_id in chosen_type_ids]
    primary_types = [item for item in selected_types if _type_bucket(item.name) in {"strength", "coached", "general"}]
    support_types = [item for item in selected_types if _type_bucket(item.name) in {"cardio", "mobility"}]
    if not primary_types:
        primary_types = selected_types[:]

    await session.execute(update(TrainingPlan).where(TrainingPlan.user_id == user.id).values(is_active=False))

    summary = (
        f"План собран под {len(chosen_days)} тренировочных дня: {_format_day_list(chosen_days)}. "
        f"На день закладываю около {minutes_limit} минут. "
        f"В основе — выбранные тобой направления: {', '.join(item.name for item in selected_types)}."
    )
    plan = TrainingPlan(
        user_id=user.id,
        title="Актуальный недельный план",
        summary=summary,
        is_active=True,
    )
    session.add(plan)
    await session.flush()

    primary_index = 0
    support_index = 0
    for weekday in chosen_days:
        day_items: list[tuple[WorkoutType, int, bool]] = []
        main_type = primary_types[primary_index % len(primary_types)]
        primary_index += 1
        main_bucket = _type_bucket(main_type.name)

        extra_minutes = 0
        if support_types and minutes_limit >= 50 and main_bucket in {"strength", "coached", "general"}:
            extra_minutes = 15 if minutes_limit < 75 else 20
        main_minutes = max(25, minutes_limit - extra_minutes)
        day_items.append((main_type, main_minutes, False))

        if extra_minutes and support_types:
            support_type = support_types[support_index % len(support_types)]
            support_index += 1
            if support_type.id != main_type.id:
                day_items.append((support_type, extra_minutes, True))

        for sort_order, (workout_type, duration_minutes, extra) in enumerate(day_items, start=1):
            bucket = _type_bucket(workout_type.name)
            session.add(
                TrainingPlanItem(
                    plan_id=plan.id,
                    weekday=weekday,
                    workout_type_id=workout_type.id,
                    title=_plan_title_for_type(workout_type.name),
                    description=_plan_description_for_type(
                        workout_type.name,
                        bucket,
                        history_counts.get(workout_type.id, 0),
                        extra,
                    ),
                    duration_minutes=duration_minutes,
                    intensity=_intensity_for_bucket(bucket, extra),
                    sort_order=sort_order,
                )
            )

    await session.commit()
    return await get_active_plan(session, user.id)


async def get_active_plan(session: AsyncSession, user_id: int) -> TrainingPlan | None:
    result = await session.execute(
        select(TrainingPlan)
        .options(selectinload(TrainingPlan.items))
        .where(TrainingPlan.user_id == user_id, TrainingPlan.is_active.is_(True))
        .order_by(desc(TrainingPlan.updated_at))
    )
    return result.scalars().first()


async def infer_plan_preferences(session: AsyncSession, user_id: int) -> dict | None:
    plan = await get_active_plan(session, user_id)
    if not plan or not plan.items:
        return None

    days = sorted({item.weekday for item in plan.items})
    type_ids = sorted({item.workout_type_id for item in plan.items if item.workout_type_id is not None})
    daily_minutes = max(item.duration_minutes for item in plan.items)
    return {"days": days, "type_ids": type_ids, "daily_minutes": daily_minutes}


def render_plan(plan: TrainingPlan) -> str:
    lines = [f"<b>{plan.title}</b>", "", plan.summary, ""]
    grouped: dict[int, list[TrainingPlanItem]] = defaultdict(list)
    for item in plan.items:
        grouped[item.weekday].append(item)

    for weekday in sorted(grouped):
        lines.append(f"<b>{WEEKDAY_MAP.get(weekday, str(weekday))}</b>")
        for item in sorted(grouped[weekday], key=lambda row: row.sort_order):
            lines.append(f"• <b>{item.title}</b> ({item.duration_minutes} мин, {item.intensity})")
            lines.append(item.description)
        lines.append("")
    return "\n".join(lines).strip()


def render_today_plan(plan: TrainingPlan | None) -> str | None:
    if not plan:
        return None
    weekday = moscow_now().isoweekday()
    items = sorted([item for item in plan.items if item.weekday == weekday], key=lambda row: row.sort_order)
    if not items:
        return None
    lines = ["<b>План на сегодня</b>", ""]
    for item in items:
        lines.append(f"• <b>{item.title}</b> ({item.duration_minutes} мин)")
        lines.append(item.description)
    return "\n".join(lines)
