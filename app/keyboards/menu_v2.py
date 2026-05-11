from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.config import get_settings

settings = get_settings()


def get_main_menu(telegram_id: int | None = None, *, is_admin: bool | None = None) -> ReplyKeyboardMarkup:
    admin_access = is_admin if is_admin is not None else telegram_id in settings.admin_id_list

    keyboard = [
        [KeyboardButton(text="Что сегодня"), KeyboardButton(text="Отметить тренировку")],
        [KeyboardButton(text="Напоминания"), KeyboardButton(text="Типы тренировок")],
        [KeyboardButton(text="План"), KeyboardButton(text="Прогресс")],
        [KeyboardButton(text="Аналитика"), KeyboardButton(text="Цель")],
        [KeyboardButton(text="Помощь")],
    ]

    if admin_access:
        keyboard.append([KeyboardButton(text="Админка"), KeyboardButton(text="Веб-панель")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выбери раздел",
    )
