from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть веб-панель", url=url)],
        ]
    )
