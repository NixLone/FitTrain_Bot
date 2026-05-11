from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common import skip_or_save_kb
from app.keyboards.main_menu import get_main_menu
from app.services.progress import add_weight_measurement, get_progress_summary
from app.services.users import get_user_by_tg_id
from app.states.progress import ProgressSG
from app.utils.dt import format_moscow_dt

router = Router()


def _render_progress(summary: dict) -> str:
    lines = ["<b>Прогресс</b>", ""]
    lines.append(
        f"За 7 дней: <b>{summary['completed_week']}</b> из <b>{summary['weekly_goal']}</b> тренировок"
    )
    lines.append(f"Общее время за неделю: <b>{summary['total_minutes']}</b> минут")

    if summary["current_weight"] is not None:
        lines.append(f"Текущий вес: <b>{summary['current_weight']}</b> кг")
    if summary["delta_weight"] is not None:
        sign = "+" if summary["delta_weight"] > 0 else ""
        lines.append(f"Изменение к прошлому замеру: <b>{sign}{summary['delta_weight']}</b> кг")

    if summary["latest_measurements"]:
        lines.append("")
        lines.append("Последние замеры:")
        for item in summary["latest_measurements"][:3]:
            weight = item.weight_kg if item.weight_kg is not None else "—"
            lines.append(f"• {format_moscow_dt(item.measured_at)} — {weight} кг")

    if summary["recent_workouts"]:
        lines.append("")
        lines.append("Последние тренировки:")
        for log, type_name in summary["recent_workouts"][:5]:
            duration = f", {log.duration_minutes} мин" if log.duration_minutes else ""
            lines.append(f"• {format_moscow_dt(log.performed_at)} — {type_name}{duration}")

    lines.append("")
    lines.append("Чтобы добавить вес, напиши /log_weight")
    return "\n".join(lines)


@router.message(lambda m: m.text == "Прогресс")
async def show_progress(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start", reply_markup=get_main_menu())
        return
    summary = await get_progress_summary(session, user)
    await message.answer(_render_progress(summary), reply_markup=get_main_menu())


@router.message(Command("log_weight"))
async def log_weight_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ProgressSG.entering_weight)
    await message.answer("Введи текущий вес в кг. Например: 81.7")


@router.message(ProgressSG.entering_weight)
async def log_weight_value(message: Message, state: FSMContext) -> None:
    try:
        weight = float(message.text.strip().replace(",", "."))
        if weight < 30 or weight > 300:
            raise ValueError
    except Exception:
        await message.answer("Введи вес числом. Например: 81.7")
        return
    await state.update_data(weight_kg=weight)
    await state.set_state(ProgressSG.entering_comment)
    await message.answer("Добавить комментарий к замеру?", reply_markup=skip_or_save_kb())


@router.message(ProgressSG.entering_comment)
async def log_weight_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Сначала нажми /start", reply_markup=get_main_menu())
        return

    data = await state.get_data()
    comment = None if message.text == "Без комментария" else message.text.strip()
    await add_weight_measurement(
        session,
        user=user,
        weight_kg=data["weight_kg"],
        comment=comment,
    )
    await state.clear()
    await message.answer("Замер записал.", reply_markup=get_main_menu())
