from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.menu_v2 import get_main_menu
from app.services.analytics import get_stats
from app.services.users import ensure_user

router = Router()


def render_stats(data: dict) -> str:
    lines = ["<b>Аналитика</b>", ""]
    lines.append(f"Всего занятий: <b>{data['total_completed']}</b>")
    lines.append(f"На этой неделе: <b>{data['week_completed']}</b>")
    if data["top_types"]:
        lines.append("")
        lines.append("Тренировок по типам:")
        for name, cnt in data["top_types"]:
            lines.append(f"• {name} — {cnt}")
    if data.get("average_gap_days") is not None:
        lines.append("")
        lines.append(f"Средний интервал между тренировками: <b>{data['average_gap_days']}</b> дня")
    return "\n".join(lines)


@router.message(lambda m: m.text == "Аналитика")
async def analytics_screen(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    user = await ensure_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    stats = await get_stats(session, user.id)
    await message.answer(render_stats(stats), reply_markup=get_main_menu(message.from_user.id))
