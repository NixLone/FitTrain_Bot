from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def skip_comment_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить комментарий")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def duration_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="30"), KeyboardButton(text="45"), KeyboardButton(text="60")],
            [KeyboardButton(text="90"), KeyboardButton(text="120"), KeyboardButton(text="Пропустить")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Минуты",
    )


def back_to_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="В меню")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def simple_choice_kb(options: list[tuple[str, str]], row_width: int = 2) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for idx, (text, data) in enumerate(options, start=1):
        row.append(InlineKeyboardButton(text=text, callback_data=data))
        if idx % row_width == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def goal_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="3"), KeyboardButton(text="4"), KeyboardButton(text="5")],
            [KeyboardButton(text="6")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Тренировок в неделю",
    )


def skip_or_save_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Без комментария")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def mood_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отлично"), KeyboardButton(text="Нормально"), KeyboardButton(text="Тяжело")],
            [KeyboardButton(text="Без настроения")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
