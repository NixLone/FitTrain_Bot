from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common import skip_or_save_kb
from app.keyboards.menu_v2 import get_main_menu
from app.keyboards.progress import progress_actions_kb
from app.services.progress import add_weight_measurement, get_progress_summary
from app.services.users import ensure_user
from app.states.progress import ProgressSG
from app.utils.dt import format_moscow_dt

router = Router()


def _render_progress(summary: dict) -> str:
    lines = ["<b>Прогресс</b>", ""]
    if summary["first_weight"] is not None:
        lines.append(f"Вес был: <b>{summary['first_weight']}</b> кг")
    if summary["latest_weight"] is not None:
        lines.append(f"Вес стал: <b>{summary['latest_weight']}</b> кг")
    if summary["delta_weight"] is not None:
        sign = "+" if summary["delta_weight"] > 0 else ""
        lines.append(f"Изменение веса: <b>{sign}{summary['delta_weight']}</b> кг")
    lines.append("")
    lines.append(f"Занятий на этой неделе: <b>{summary['completed_week']}</b>")
    if summary["recent_workouts"]:
        lines.append("")
        lines.append("Последние тренировки:")
        for log, type_name in summary["recent_workouts"][:5]:
            mood = f", настроение: {log.mood}" if getattr(log, "mood", None) else ""
            lines.append(f"• {format_moscow_dt(log.performed_at)} — {type_name}{mood}")
    return "\n".join(lines)


async def _ensure_current_user(session: AsyncSession, message: Message):
    tg_user = message.from_user
    return await ensure_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )


@router.message(lambda m: m.text == "Прогресс")
async def show_progress(message: Message, session: AsyncSession) -> None:
    user = await _ensure_current_user(session, message)
    summary = await get_progress_summary(session, user)
    await message.answer(_render_progress(summary), reply_markup=progress_actions_kb())


@router.callback_query(lambda c: c.data == "progress:log_weight")
async def log_weight_button(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProgressSG.entering_weight)
    await callback.message.answer("Введи текущий вес в кг. Например: 60 или 81.7")
    await callback.answer()


@router.message(Command("log_weight"))
@router.message(lambda m: m.text == "Ввести вес")
async def log_weight_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ProgressSG.entering_weight)
    await message.answer("Введи текущий вес в кг. Например: 60 или 81.7")


@router.message(ProgressSG.entering_weight)
async def log_weight_value(message: Message, state: FSMContext) -> None:
    try:
        weight = float(message.text.strip().replace(",", "."))
        if weight < 30 or weight > 300:
            raise ValueError
    except Exception:
        await message.answer("Введи вес числом. Например: 60 или 81.7")
        return
    await state.update_data(weight_kg=weight)
    await state.set_state(ProgressSG.entering_comment)
    await message.answer("Добавить комментарий к замеру?", reply_markup=skip_or_save_kb())


@router.message(ProgressSG.entering_comment)
async def log_weight_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_current_user(session, message)
    data = await state.get_data()
    comment = None if message.text == "Без комментария" else message.text.strip()
    await add_weight_measurement(session, user=user, weight_kg=data["weight_kg"], comment=comment)
    await state.clear()
    await message.answer("Вес записал.", reply_markup=get_main_menu(message.from_user.id))
