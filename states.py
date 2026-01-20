from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    full_name = State()
    phone = State()
    city = State()
    age = State()


class ActivityState(StatesGroup):
    category = State()
    value = State()


class RatingState(StatesGroup):
    category = State()


class BroadcastState(StatesGroup):
    waiting_for_message = State()