from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.menu_v2 import get_main_menu
from app.keyboards.plans import duration_picker_kb, plan_actions_kb, weekday_picker_kb, workout_type_picker_kb
from app.services.plans_smart import (
    generate_plan_for_user,
    get_active_plan,
    get_ranked_workout_types,
    infer_plan_preferences,
    render_plan,
)
from app.services.users import ensure_user
from app.states.plans import PlanWizardSG

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


async def _start_plan_wizard(
    target_message: Message,
    state: FSMContext,
    *,
    defaults: dict | None = None,
) -> None:
    days = set((defaults or {}).get("days", []))
    daily_minutes = (defaults or {}).get("daily_minutes")
    type_ids = set((defaults or {}).get("type_ids", []))

    await state.clear()
    await state.set_state(PlanWizardSG.choosing_days)
    await state.update_data(selected_days=list(days), daily_minutes=daily_minutes, selected_type_ids=list(type_ids))
    await target_message.answer(
        "Выбери удобные дни для тренировок. Можно отметить несколько и потом нажать «Готово».",
        reply_markup=weekday_picker_kb(days),
    )


@router.message(lambda m: m.text == "План")
async def show_plan(message: Message, session: AsyncSession) -> None:
    user = await _ensure_current_user(session, message)
    plan = await get_active_plan(session, user.id)
    if not plan:
        await message.answer(
            "План пока не собран. Нажми кнопку ниже, и я помогу его настроить под твои дни и интересы.",
            reply_markup=plan_actions_kb(False),
        )
        return

    await message.answer(render_plan(plan), reply_markup=plan_actions_kb(True))


@router.message(Command("generate_plan"))
async def generate_plan_entry(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _ensure_current_user(session, message)
    defaults = await infer_plan_preferences(session, user.id)
    await _start_plan_wizard(message, state, defaults=defaults)


@router.callback_query(lambda c: c.data == "plan:wizard:start")
async def plan_wizard_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await ensure_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    defaults = await infer_plan_preferences(session, user.id)
    await _start_plan_wizard(callback.message, state, defaults=defaults)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("plan:day:"))
async def toggle_plan_day(callback: CallbackQuery, state: FSMContext) -> None:
    day = int(callback.data.split(":")[-1])
    data = await state.get_data()
    selected_days = set(data.get("selected_days", []))
    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.add(day)
    await state.update_data(selected_days=sorted(selected_days))
    await callback.message.edit_reply_markup(reply_markup=weekday_picker_kb(selected_days))
    await callback.answer()


@router.callback_query(lambda c: c.data == "plan:days:done")
async def finish_plan_days(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected_days = set(data.get("selected_days", []))
    if not selected_days:
        await callback.answer("Выбери хотя бы один день", show_alert=True)
        return

    await state.set_state(PlanWizardSG.choosing_duration)
    await callback.message.answer(
        "Сколько времени ты готов уделять одной тренировке?",
        reply_markup=duration_picker_kb(data.get("daily_minutes")),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("plan:duration:"))
async def pick_plan_duration(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    value = callback.data.split(":")[-1]
    if value == "done":
        data = await state.get_data()
        selected_minutes = data.get("daily_minutes")
        if not selected_minutes:
            await callback.answer("Сначала выбери длительность", show_alert=True)
            return

        await state.set_state(PlanWizardSG.choosing_types)
        user = await ensure_user(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )
        types_ = await get_ranked_workout_types(session, user.id)
        options = [(item.id, item.name) for item in types_]
        selected_ids = set(data.get("selected_type_ids", []))
        await callback.message.answer(
            "Отметь интересующие направления. Можно выбрать несколько и потом нажать «Готово».",
            reply_markup=workout_type_picker_kb(options, selected_ids),
        )
        await callback.answer()
        return

    minutes = int(value)
    await state.update_data(daily_minutes=minutes)
    await callback.message.edit_reply_markup(reply_markup=duration_picker_kb(minutes))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("plan:type:"))
async def toggle_plan_type(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    type_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    selected_ids = set(data.get("selected_type_ids", []))
    if type_id in selected_ids:
        selected_ids.remove(type_id)
    else:
        selected_ids.add(type_id)
    await state.update_data(selected_type_ids=sorted(selected_ids))

    user = await ensure_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    options = [(item.id, item.name) for item in await get_ranked_workout_types(session, user.id)]
    await callback.message.edit_reply_markup(reply_markup=workout_type_picker_kb(options, selected_ids))
    await callback.answer()


@router.callback_query(lambda c: c.data == "plan:types:done")
async def finish_plan_types(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    selected_ids = data.get("selected_type_ids", [])
    if not selected_ids:
        await callback.answer("Выбери хотя бы одно направление", show_alert=True)
        return

    user = await ensure_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    plan = await generate_plan_for_user(
        session,
        user,
        selected_days=data.get("selected_days", []),
        selected_type_ids=selected_ids,
        daily_minutes=data.get("daily_minutes"),
    )
    await state.clear()
    await callback.message.answer(
        "Собрал новый недельный план под твои дни, длительность и интересующие направления.\n\n"
        + render_plan(plan),
        reply_markup=get_main_menu(callback.from_user.id),
    )
    await callback.answer()
