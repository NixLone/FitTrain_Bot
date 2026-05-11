from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.menu_v2 import get_main_menu
from app.services.users import get_or_create_user
from app.texts.messages_v2 import HELP_TEXT, WELCOME_TEXT

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    await get_or_create_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu(message.from_user.id))


@router.message(Command("help"))
@router.message(lambda m: m.text == "Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=get_main_menu(message.from_user.id))
