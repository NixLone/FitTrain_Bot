from aiogram.fsm.state import State, StatesGroup


class ManualWorkoutSG(StatesGroup):
    choosing_workout_type = State()
    entering_duration = State()
    entering_comment = State()
    entering_mood = State()
    entering_datetime = State()


class CompleteEventSG(StatesGroup):
    entering_duration = State()
    entering_comment = State()
    entering_mood = State()
    entering_datetime = State()
