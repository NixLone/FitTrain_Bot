from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common import duration_kb, mood_kb, simple_choice_kb, skip_comment_kb
from app.keyboards.menu_v2 import get_main_menu
from app.services.users import ensure_user
from app.services.workout_types import create_custom_workout_type, list_available_workout_types
from app.services.workouts import create_manual_workout_log
from app.states.workouts import ManualWorkoutSG
from app.utils.dt import moscow_to_utc, parse_datetime_ddmmyyyy_hhmm, utc_now

router = Router()


async def _ensure_current_user(session: AsyncSession, message: Message):
    tg_user = message.from_user
    return await ensure_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )


@router.message(lambda m: m.text == "Типы тренировок")
async def workout_types_menu(message: Message, session: AsyncSession) -> None:
    user = await _ensure_current_user(session, message)
    types_ = await list_available_workout_types(session, user.id)
    default_items = [t.name for t in types_ if t.user_id is None]
    custom_items = [t.name for t in types_ if t.user_id == user.id]

    text = "<b>Типы тренировок</b>\n\nСтандартные:\n"
    text += "\n".join(f"• {name}" for name in default_items)
    if custom_items:
        text += "\n\nТвои:\n" + "\n".join(f"• {name}" for name in custom_items)
    text += "\n\nЧтобы добавить свой тип, напиши: /add_type Название"

    await message.answer(text, reply_markup=get_main_menu(message.from_user.id))


@router.message(Command("add_type"))
async def add_workout_type(message: Message, session: AsyncSession) -> None:
    user = await _ensure_current_user(session, message)
    parts = (message.text or "").split(maxsplit=1)
    name = parts[1].strip() if len(parts) > 1 else ""
    if not name:
        await message.answer("Напиши так: /add_type Турник")
        return

    await create_custom_workout_type(session, user.id, name)
    await message.answer(
        f"Добавил новый тип: <b>{name}</b>",
        reply_markup=get_main_menu(message.from_user.id),
    )


@router.message(lambda m: m.text == "Цель")
async def goal_info(message: Message, session: AsyncSession) -> None:
    user = await _ensure_current_user(session, message)
    await message.answer(
        f"Текущая цель: <b>{user.weekly_goal}</b> тренировок в неделю.\n"
        "Чтобы поменять, напиши: /goal 4",
        reply_markup=get_main_menu(message.from_user.id),
    )


@router.message(Command("goal"))
async def set_goal(message: Message, session: AsyncSession) -> None:
    user = await _ensure_current_user(session, message)
    try:
        goal = int((message.text or "").split(maxsplit=1)[1])
        if goal < 0:
            raise ValueError
    except Exception:
        await message.answer("Пример: /goal 4")
        return

    user.weekly_goal = goal
    await session.commit()
    await message.answer(
        f"Цель обновил: <b>{goal}</b> тренировок в неделю",
        reply_markup=get_main_menu(message.from_user.id),
    )


@router.message(lambda m: m.text == "Отметить тренировку")
async def start_manual_log(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_current_user(session, message)
    types_ = await list_available_workout_types(session, user.id)
    kb = simple_choice_kb([(item.name, f"manual_type:{item.id}") for item in types_], row_width=2)
    await state.set_state(ManualWorkoutSG.choosing_workout_type)
    await message.answer("Выбери тип тренировки:", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("manual_type:"))
async def manual_choose_type(callback: CallbackQuery, state: FSMContext) -> None:
    workout_type_id = int(callback.data.split(":")[1])
    await state.update_data(workout_type_id=workout_type_id)
    await state.set_state(ManualWorkoutSG.entering_duration)
    await callback.message.answer(
        "Укажи длительность в минутах или нажми Пропустить",
        reply_markup=duration_kb(),
    )
    await callback.answer()


@router.message(ManualWorkoutSG.entering_duration)
async def manual_duration(message: Message, state: FSMContext) -> None:
    value = None
    if message.text != "Пропустить":
        try:
            value = int(message.text)
        except Exception:
            await message.answer("Введи число минут, например 60, или нажми Пропустить")
            return

    await state.update_data(duration=value)
    await state.set_state(ManualWorkoutSG.entering_comment)
    await message.answer(
        "Добавь комментарий или нажми 'Пропустить комментарий'",
        reply_markup=skip_comment_kb(),
    )


@router.message(ManualWorkoutSG.entering_comment)
async def manual_comment(message: Message, state: FSMContext) -> None:
    comment = None if message.text == "Пропустить комментарий" else message.text.strip()
    await state.update_data(comment=comment)
    await state.set_state(ManualWorkoutSG.entering_mood)
    await message.answer("Как прошло по ощущениям?", reply_markup=mood_kb())


@router.message(ManualWorkoutSG.entering_mood)
async def manual_mood(message: Message, state: FSMContext) -> None:
    mood = None if message.text == "Без настроения" else message.text.strip()
    await state.update_data(mood=mood)
    await state.set_state(ManualWorkoutSG.entering_datetime)
    await message.answer(
        "Когда была тренировка?\nНапиши 'сейчас' или дату в формате 17.03.2026 19:30",
        reply_markup=get_main_menu(message.from_user.id),
    )


@router.message(ManualWorkoutSG.entering_datetime)
async def manual_datetime(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_current_user(session, message)

    text = message.text.strip().lower()
    if text == "сейчас":
        performed_at = utc_now()
    else:
        try:
            performed_at = moscow_to_utc(parse_datetime_ddmmyyyy_hhmm(message.text))
        except Exception:
            await message.answer("Формат: 17.03.2026 19:30 или 'сейчас'")
            return

    data = await state.get_data()
    await create_manual_workout_log(
        session,
        user_id=user.id,
        workout_type_id=data["workout_type_id"],
        performed_at=performed_at,
        duration_minutes=data.get("duration"),
        mood=data.get("mood"),
        comment=data.get("comment"),
    )
    await state.clear()
    await message.answer("Тренировку записал.", reply_markup=get_main_menu(message.from_user.id))
