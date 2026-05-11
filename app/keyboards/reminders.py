from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def quick_dates_kb(options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=text, callback_data=data)] for text, data in options]
    rows.append([InlineKeyboardButton(text="Гибкая настройка", callback_data="quick:manual")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def suggested_times_kb(options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for idx, (text, data) in enumerate(options, start=1):
        row.append(InlineKeyboardButton(text=text, callback_data=data))
        if idx % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Ввести вручную", callback_data="time:manual")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminders_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать напоминание", callback_data="reminders:create")],
            [InlineKeyboardButton(text="📋 Мои напоминания", callback_data="reminders:list")],
        ]
    )


def schedule_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 По дням недели", callback_data="schedule:weekly")],
            [InlineKeyboardButton(text="🗓 Разовое", callback_data="schedule:one_time")],
            [InlineKeyboardButton(text="⏳ Через интервал", callback_data="schedule:interval")],
        ]
    )


def reminder_actions_kb(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнил", callback_data=f"event:complete:{event_id}"),
                InlineKeyboardButton(text="⏭ Пропустил", callback_data=f"event:skip:{event_id}"),
            ],
            [
                InlineKeyboardButton(text="🕒 Перенести", callback_data=f"event:reschedule:{event_id}"),
            ],
        ]
    )


def skip_reason_kb(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Устал", callback_data=f"skip_reason:{event_id}:Устал")],
            [InlineKeyboardButton(text="Не успел", callback_data=f"skip_reason:{event_id}:Не успел")],
            [InlineKeyboardButton(text="Плохое самочувствие", callback_data=f"skip_reason:{event_id}:Плохое самочувствие")],
            [InlineKeyboardButton(text="Без причины", callback_data=f"skip_reason:{event_id}:Без причины")],
        ]
    )


def reschedule_kb(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="+30 минут", callback_data=f"resch:{event_id}:30m")],
            [InlineKeyboardButton(text="Сегодня 21:00", callback_data=f"resch:{event_id}:today21")],
            [InlineKeyboardButton(text="Завтра 09:00", callback_data=f"resch:{event_id}:tomorrow9")],
            [InlineKeyboardButton(text="Завтра 19:00", callback_data=f"resch:{event_id}:tomorrow19")],
            [InlineKeyboardButton(text="Ввести вручную", callback_data=f"resch:{event_id}:custom")],
        ]
    )
