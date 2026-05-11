from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Что сегодня"), KeyboardButton(text="Отметить тренировку")],
            [KeyboardButton(text="Напоминания"), KeyboardButton(text="Типы тренировок")],
            [KeyboardButton(text="Аналитика"), KeyboardButton(text="Цель")],
            [KeyboardButton(text="Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери раздел",
    )


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Что сегодня"), KeyboardButton(text="Отметить тренировку")],
            [KeyboardButton(text="Напоминания"), KeyboardButton(text="Типы тренировок")],
            [KeyboardButton(text="Профиль"), KeyboardButton(text="План")],
            [KeyboardButton(text="Прогресс"), KeyboardButton(text="Аналитика")],
            [KeyboardButton(text="Цель"), KeyboardButton(text="Помощь")],
            [KeyboardButton(text="Админка")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери раздел",
    )
