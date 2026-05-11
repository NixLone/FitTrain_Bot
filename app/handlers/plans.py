from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.main_menu import get_main_menu
from app.services.plans import generate_plan_for_user, get_active_plan, render_plan
from app.services.users import get_user_by_tg_id

router = Router()


@router.message(lambda m: m.text == "План")
async def show_plan(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start", reply_markup=get_main_menu())
        return

    if not user.height_cm or user.current_weight_kg is None:
        await message.answer(
            "Сначала заполни профиль в разделе «Профиль» или командой /profile_setup.",
            reply_markup=get_main_menu(),
        )
        return

    plan = await get_active_plan(session, user.id)
    if not plan:
        await message.answer(
            "План пока не создан. Напиши /generate_plan, и я соберу недельную структуру.",
            reply_markup=get_main_menu(),
        )
        return

    await message.answer(render_plan(plan), reply_markup=get_main_menu())


@router.message(Command("generate_plan"))
async def generate_plan(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start", reply_markup=get_main_menu())
        return

    if not user.height_cm or user.current_weight_kg is None:
        await message.answer(
            "Для генерации плана нужен заполненный профиль. Запусти /profile_setup.",
            reply_markup=get_main_menu(),
        )
        return

    plan = await generate_plan_for_user(session, user)
    await message.answer(
        "Собрал новый недельный план.\n\n" + render_plan(plan),
        reply_markup=get_main_menu(),
    )
