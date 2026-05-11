from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.main_menu import get_main_menu
from app.services.analytics import get_stats
from app.services.users import get_user_by_tg_id

router = Router()

WEEKDAY_RU = {
    "0": "Вс",
    "1": "Пн",
    "2": "Вт",
    "3": "Ср",
    "4": "Чт",
    "5": "Пт",
    "6": "Сб",
}


def render_stats(title: str, data: dict) -> str:
    lines = [f"<b>{title}</b>", ""]
    lines.append(f"Выполнено: <b>{data['completed']}</b>")
    lines.append(f"Пропусков: <b>{data['skipped']}</b>")
    if data.get("percent") is not None:
        lines.append(f"Цель: <b>{data['goal']}</b> | Выполнение: <b>{data['percent']}%</b>")
    if data.get("avg_duration"):
        lines.append(f"Средняя длительность: <b>{data['avg_duration']} мин</b>")
    if data["top_types"]:
        lines.append("")
        lines.append("Частые типы:")
        for name, cnt in data["top_types"]:
            lines.append(f"• {name} — {cnt}")
    if data["weekday_rows"]:
        lines.append("")
        lines.append("Активные дни:")
        for wd, cnt in data["weekday_rows"][:3]:
            lines.append(f"• {WEEKDAY_RU.get(str(wd), str(wd))} — {cnt}")
    return "\n".join(lines)


@router.message(lambda m: m.text == "Аналитика")
async def analytics_menu(message: Message) -> None:
    await message.answer(
        "Напиши: <b>неделя</b> или <b>месяц</b>\n"
        "Например: неделя",
        reply_markup=get_main_menu(),
    )


@router.message(lambda m: m.text and m.text.lower() in {"неделя", "месяц"})
async def analytics_text(message: Message, session: AsyncSession) -> None:
    user = await get_user_by_tg_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала нажми /start", reply_markup=get_main_menu())
        return
    days = 7 if message.text.lower() == "неделя" else 30
    data = await get_stats(session, user.id, days)
    title = "Статистика за неделю 📊" if days == 7 else "Статистика за месяц 📈"
    await message.answer(render_stats(title, data), reply_markup=get_main_menu())
