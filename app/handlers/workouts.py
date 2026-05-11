from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common import duration_kb, mood_kb, skip_comment_kb, simple_choice_kb
from app.keyboards.main_menu import get_main_menu
from app.services.users import get_user_by_tg_id
from app.services.workout_types import create_custom_workout_type, list_available_workout_types
from app.services.workouts import create_manual_workout_log
from app.states.workouts import ManualWorkoutSG
from app.utils.dt import parse_datetime_ddmmyyyy_hhmm, utc_now

router = Router()


@router.message(lambda m: m.text == "Типы тренировок")
async def workout_types_menu(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    types_ = await list_available_workout_types(session, user.id)
    default_items = [t.name for t in types_ if t.user_id is None]
    custom_items = [t.name for t in types_ if t.user_id == user.id]
    text = "<b>Типы тренировок</b>\n\nСтандартные:\n"
    text += "\n".join(f"• {name}" for name in default_items)
    if custom_items:
        text += "\n\nТвои:\n" + "\n".join(f"• {name}" for name in custom_items)
    text += "\n\nЧтобы добавить свой тип, напиши: /add_type Название"
    await message.answer(text, reply_markup=get_main_menu())


@router.message(lambda m: m.text and m.text.startswith("/add_type "))
async def add_workout_type(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    name = message.text.replace("/add_type", "", 1).strip()
    if not name:
        await message.answer("Напиши так: /add_type Турник")
        return
    await create_custom_workout_type(session, user.id, name)
    await message.answer(f"Добавил новый тип: <b>{name}</b>", reply_markup=get_main_menu())


@router.message(lambda m: m.text == "Цель")
async def goal_info(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    await message.answer(
        f"Текущая цель: <b>{user.weekly_goal}</b> тренировок в неделю.\n"
        f"Чтобы поменять, напиши: /goal 4",
        reply_markup=get_main_menu(),
    )


@router.message(lambda m: m.text and m.text.startswith("/goal "))
async def set_goal(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    try:
        goal = int(message.text.split(maxsplit=1)[1])
        if goal < 0:
            raise ValueError
    except Exception:
        await message.answer("Пример: /goal 4")
        return
    user.weekly_goal = goal
    await session.commit()
    await message.answer(f"Цель обновил: <b>{goal}</b> тренировок в неделю", reply_markup=get_main_menu())


@router.message(lambda m: m.text == "Отметить тренировку")
async def start_manual_log(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    types_ = await list_available_workout_types(session, user.id)
    kb = simple_choice_kb([(item.name, f"manual_type:{item.id}") for item in types_], row_width=2)
    await state.set_state(ManualWorkoutSG.choosing_workout_type)
    await message.answer("Выбери тип тренировки:", reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("manual_type:"))
async def manual_choose_type(callback: CallbackQuery, state: FSMContext) -> None:
    workout_type_id = int(callback.data.split(":")[1])
    await state.update_data(workout_type_id=workout_type_id)
    await state.set_state(ManualWorkoutSG.entering_duration)
    await callback.message.answer("Укажи длительность в минутах или нажми Пропустить", reply_markup=duration_kb())
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
    await message.answer("Добавь комментарий или нажми 'Пропустить комментарий'", reply_markup=skip_comment_kb())


@router.message(ManualWorkoutSG.entering_comment)
async def manual_comment(message: Message, state: FSMContext) -> None:
    comment = None if message.text == "Пропустить комментарий" else message.text.strip()
    await state.update_data(comment=comment)
    await state.set_state(ManualWorkoutSG.entering_datetime)
    await message.answer(
        "Когда была тренировка?\n"
        "Напиши 'сейчас' или дату в формате 17.03.2026 19:30",
        reply_markup=get_main_menu(),
    )


@router.message(ManualWorkoutSG.entering_datetime)
async def manual_datetime(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await state.clear()
        await message.answer("Сначала нажми /start")
        return

    text = message.text.strip().lower()
    if text == "сейчас":
        performed_at = utc_now()
    else:
        try:
            performed_at = parse_datetime_ddmmyyyy_hhmm(message.text)
            from app.utils.dt import moscow_to_utc
            performed_at = moscow_to_utc(performed_at)
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
        comment=data.get("comment"),
    )
    await state.clear()
    await message.answer("Тренировку записал ✅", reply_markup=get_main_menu())
