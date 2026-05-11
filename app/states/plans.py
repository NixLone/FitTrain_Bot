from aiogram.fsm.state import State, StatesGroup


class PlanWizardSG(StatesGroup):
    choosing_days = State()
    choosing_duration = State()
    choosing_types = State()
