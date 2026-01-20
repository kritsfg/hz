from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


CATEGORY_LABELS = {
    "pushups": "Отжимания",
    "squats": "Приседания",
    "pullups": "Подтягивания",
    "running": "Бег",
    "reading": "Прочитанные страницы",
}


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="✍️ Записать"), KeyboardButton(text="🏆 Рейтинг")],
        [KeyboardButton(text="ℹ️ О себе")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="📢 Рассылка")])
        rows.append([KeyboardButton(text="👥 Участники"), KeyboardButton(text="🚫 Черный список")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


REGISTER_BUTTON = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🚀 Регистрация")]],
    resize_keyboard=True,
)

ACTIVITY_CHOICES = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💪 Отжимания", callback_data="activity:pushups")],
        [InlineKeyboardButton(text="🏋️ Приседания", callback_data="activity:squats")],
        [InlineKeyboardButton(text="🧗 Подтягивания", callback_data="activity:pullups")],
        [InlineKeyboardButton(text="🏃‍♂️ Бег (км)", callback_data="activity:running")],
        [InlineKeyboardButton(text="📚 Прочитано", callback_data="activity:reading")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")],
    ]
)

RATING_MENU = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="💪 Отжимания", callback_data="rating:pushups")],
        [InlineKeyboardButton(text="🏋️ Приседания", callback_data="rating:squats")],
        [InlineKeyboardButton(text="🧗 Подтягивания", callback_data="rating:pullups")],
        [InlineKeyboardButton(text="🏃‍♂️ Бег", callback_data="rating:running")],
        [InlineKeyboardButton(text="📚 Чтение", callback_data="rating:reading")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")],
    ]
)


def approval_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{user_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")],
        ]
    )