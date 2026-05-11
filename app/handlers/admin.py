from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.admin import admin_panel_kb
from app.keyboards.menu_v2 import get_main_menu
from app.services.admin import get_admin_dashboard
from app.services.cms import CmsMagicLinkError, create_cms_magic_link

router = Router()
settings = get_settings()


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_id_list


@router.message(Command("admin"))
@router.message(lambda m: m.text == "Админка")
async def admin_dashboard(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer(
            "Раздел доступен только администратору. Добавь свой Telegram ID в ADMIN_IDS.",
            reply_markup=get_main_menu(),
        )
        return

    data = await get_admin_dashboard(session)
    lines = ["<b>Админка</b>", ""]
    lines.append(f"Пользователей: <b>{data['users_count']}</b>")
    lines.append(f"Новых за 7 дней: <b>{data['new_users_week']}</b>")
    lines.append(f"Активных напоминаний: <b>{data['active_reminders']}</b>")
    lines.append(f"Записей тренировок за 7 дней: <b>{data['workouts_week']}</b>")
    if data["recent_users"]:
        lines.append("")
        lines.append("Последние пользователи:")
        for user in data["recent_users"]:
            name = user.first_name or user.username or str(user.telegram_id)
            lines.append(f"• {name} ({user.telegram_id})")
    await message.answer("\n".join(lines), reply_markup=get_main_menu())


@router.message(Command("panel"))
@router.message(lambda m: m.text == "Веб-панель")
async def open_web_panel(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer(
            "Веб-панель доступна только администратору.",
            reply_markup=get_main_menu(),
        )
        return

    try:
        login_url = await create_cms_magic_link(staff_telegram_id=message.from_user.id)
    except CmsMagicLinkError as exc:
        await message.answer(
            f"Не удалось создать ссылку для входа: {exc}",
            reply_markup=get_main_menu(),
        )
        return

    await message.answer(
        "Ссылка для входа в веб-панель готова.\n"
        "Она действует 15 минут и становится недействительной после использования.",
        reply_markup=admin_panel_kb(login_url),
    )
