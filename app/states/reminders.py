from aiogram.fsm.state import State, StatesGroup


class CreateReminderSG(StatesGroup):
    choosing_quick_date = State()
    choosing_schedule = State()
    choosing_workout_type = State()
    choosing_time = State()
    entering_title = State()
    entering_message = State()
    entering_weekdays = State()
    entering_date = State()
    entering_interval_days = State()
    entering_time = State()
    confirm = State()


class RescheduleSG(StatesGroup):
    entering_custom_datetime = State()
