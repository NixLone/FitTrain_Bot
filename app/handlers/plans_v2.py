from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.menu_v2 import get_main_menu
from app.services.plans import generate_plan_for_user, get_active_plan, render_plan
from app.services.users import ensure_user

router = Router()


@router.message(lambda m: m.text == "План")
async def show_plan(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    user = await ensure_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )

    plan = await get_active_plan(session, user.id)
    if not plan:
        await message.answer(
            "План пока не создан. Напиши /generate_plan, и я соберу недельную структуру.",
            reply_markup=get_main_menu(message.from_user.id),
        )
        return

    await message.answer(render_plan(plan), reply_markup=get_main_menu(message.from_user.id))


@router.message(Command("generate_plan"))
async def generate_plan(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    user = await ensure_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )

    plan = await generate_plan_for_user(session, user)
    await message.answer(
        "Собрал новый недельный план.\n\n" + render_plan(plan),
        reply_markup=get_main_menu(message.from_user.id),
    )
