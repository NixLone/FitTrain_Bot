from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import TrainingPlan, TrainingPlanItem, User, WorkoutType
from app.utils.dt import WEEKDAY_MAP, moscow_now


@dataclass
class PlanTemplateItem:
    weekday: int
    type_name: str
    title: str
    description: str
    duration_minutes: int
    intensity: str


def _build_templates(goal: int, weight_kg: float | None) -> list[PlanTemplateItem]:
    run_note = "Легкий темп, без гонки за скоростью."
    if weight_kg and weight_kg >= 95:
        run_note = "Чередуй легкий бег и быстрый шаг, держи умеренный темп."

    templates = [
        PlanTemplateItem(1, "Силовая", "Силовая в зале", "Базовые упражнения на всё тело: присед, тяга, жим, тяга блока.", 60, "умеренная"),
        PlanTemplateItem(2, "Бег", "Беговая работа", f"Разминка 10 минут, затем основная часть 20-30 минут. {run_note}", 40, "умеренная"),
        PlanTemplateItem(3, "Растяжка", "Восстановление и растяжка", "Мобилизация суставов, мягкая растяжка ног, спины и плеч.", 30, "легкая"),
        PlanTemplateItem(4, "Групповое занятие", "Групповая тренировка", "Посети групповое занятие средней интенсивности и отметь самочувствие после.", 50, "средняя"),
        PlanTemplateItem(5, "Занятие с тренером", "Сессия с тренером", "Отработай технику и скорректируй веса или беговую механику.", 60, "контролируемая"),
        PlanTemplateItem(6, "Силовая", "Вторая силовая", "Сделай акцент на ноги и спину, работай с запасом 1-2 повтора.", 55, "умеренно высокая"),
        PlanTemplateItem(7, "Растяжка", "Легкое восстановление", "15 минут ходьбы и 15 минут растяжки или дыхательной работы.", 30, "легкая"),
    ]
    return templates[: max(1, min(goal, len(templates)))]


async def _get_workout_types_map(session: AsyncSession, user_id: int) -> dict[str, WorkoutType]:
    result = await session.execute(
        select(WorkoutType).where(
            WorkoutType.is_active.is_(True),
            (WorkoutType.user_id.is_(None)) | (WorkoutType.user_id == user_id),
        )
    )
    items = result.scalars().all()
    return {item.name.lower(): item for item in items}


async def generate_plan_for_user(session: AsyncSession, user: User) -> TrainingPlan:
    goal = max(1, min(user.weekly_goal or 3, 7))
    templates = _build_templates(goal, user.current_weight_kg)
    types_map = await _get_workout_types_map(session, user.id)

    await session.execute(
        update(TrainingPlan).where(TrainingPlan.user_id == user.id).values(is_active=False)
    )

    summary = (
        f"План на {goal} тренировок в неделю. "
        f"Сочетает зал, бег и восстановление, чтобы держать регулярность без перегруза."
    )
    plan = TrainingPlan(
        user_id=user.id,
        title="Актуальный недельный план",
        summary=summary,
        is_active=True,
    )
    session.add(plan)
    await session.flush()

    for sort_order, item in enumerate(templates, start=1):
        workout_type = types_map.get(item.type_name.lower())
        session.add(
            TrainingPlanItem(
                plan_id=plan.id,
                weekday=item.weekday,
                workout_type_id=workout_type.id if workout_type else None,
                title=item.title,
                description=item.description,
                duration_minutes=item.duration_minutes,
                intensity=item.intensity,
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
        .order_by(TrainingPlan.updated_at.desc())
    )
    return result.scalars().first()


def render_plan(plan: TrainingPlan) -> str:
    lines = [f"<b>{plan.title}</b>", "", plan.summary, ""]
    for item in sorted(plan.items, key=lambda row: (row.weekday, row.sort_order)):
        weekday = WEEKDAY_MAP.get(item.weekday, str(item.weekday))
        lines.append(
            f"• {weekday}: <b>{item.title}</b> ({item.duration_minutes} мин, {item.intensity})"
        )
        lines.append(item.description)
        lines.append("")
    return "\n".join(lines).strip()


def render_today_plan(plan: TrainingPlan | None) -> str | None:
    if not plan:
        return None
    weekday = moscow_now().isoweekday()
    items = sorted(
        [item for item in plan.items if item.weekday == weekday],
        key=lambda row: row.sort_order,
    )
    if not items:
        return None
    lines = ["<b>План на сегодня</b>", ""]
    for item in items:
        lines.append(f"• <b>{item.title}</b> ({item.duration_minutes} мин)")
        lines.append(item.description)
    return "\n".join(lines)
