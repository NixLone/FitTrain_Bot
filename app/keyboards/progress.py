from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def progress_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ввести вес", callback_data="progress:log_weight")],
        ]
    )
