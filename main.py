import asyncio
import logging
import os
import sys
import random
from datetime import datetime
from typing import Dict, Optional

# Добавьте путь для корректных импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import db
from bot.config import settings
from bot.keyboards import (
    ACTIVITY_CHOICES,
    CATEGORY_LABELS,
    RATING_MENU,
    REGISTER_BUTTON,
    main_menu,
    approval_keyboard,
)
from bot.states import ActivityState, BroadcastState, RatingState, RegistrationState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== ФУНКЦИЯ СОЗДАНИЯ БОТА С ПРОКСИ ====================
async def create_bot_with_proxy(token: str) -> Bot:
    """
    Автоматически подбирает рабочий прокси-сервер за границей
    для обхода блокировки Telegram в России
    """
    print("=" * 60)
    print("🌍 ПОИСК РАБОЧЕГО ПРОКСИ-СЕРВЕРА ЗА ГРАНИЦЕЙ")
    print("=" * 60)

    # Список публичных прокси-серверов в разных странах
    # Эти серверы находятся за пределами России и обходят блокировку
    PROXY_SERVERS = [
        # 🇺🇸 США
        {"url": "socks5://45.77.56.114:9050", "country": "США", "city": "Нью-Йорк"},
        {"url": "socks5://138.197.157.60:9050", "country": "США", "city": "Сан-Франциско"},
        {"url": "socks5://209.97.150.167:9050", "country": "США", "city": "Чикаго"},

        # 🇩🇪 Германия
        {"url": "socks5://185.199.229.156:7492", "country": "Германия", "city": "Франкфурт"},
        {"url": "socks5://188.166.216.198:9050", "country": "Германия", "city": "Берлин"},

        # 🇳🇱 Нидерланды
        {"url": "socks5://178.62.193.19:9050", "country": "Нидерланды", "city": "Амстердам"},

        # 🇸🇬 Сингапур
        {"url": "socks5://128.199.202.122:9050", "country": "Сингапур", "city": "Сингапур"},

        # 🇯🇵 Япония
        {"url": "socks5://45.32.234.150:9050", "country": "Япония", "city": "Токио"},

        # 🇫🇷 Франция
        {"url": "socks5://51.158.68.133:8811", "country": "Франция", "city": "Париж"},

        # 🇬🇧 Великобритания
        {"url": "socks5://51.15.122.122:9050", "country": "Великобритания", "city": "Лондон"},

        # 🇨🇦 Канада
        {"url": "socks5://159.203.87.129:9050", "country": "Канада", "city": "Торонто"},
    ]

    # Перемешиваем список для рандомизации
    random.shuffle(PROXY_SERVERS)

    bot_instance = None
    working_proxy = None

    for idx, proxy in enumerate(PROXY_SERVERS, 1):
        try:
            print(f"🔄 Попытка {idx}/{len(PROXY_SERVERS)}: {proxy['country']} ({proxy['city']})")

            # Импортируем библиотеку для прокси
            from aiohttp_socks import ProxyConnector
            import aiohttp

            # Создаем подключение через прокси
            connector = ProxyConnector.from_url(proxy['url'])
            session = aiohttp.ClientSession(connector=connector)

            # Создаем бота с этой сессией
            bot_instance = Bot(
                token=token,
                parse_mode=ParseMode.HTML,
                session=session
            )

            # Тестируем подключение (быстрая проверка)
            me = await bot_instance.get_me(request_timeout=15)

            working_proxy = proxy
            print(f"✅ УСПЕХ! Найден рабочий прокси в {proxy['country']}!")
            print(f"   📡 Подключение через: {proxy['url']}")
            print(f"   🤖 Бот: @{me.username} (ID: {me.id})")
            print("=" * 60)

            return bot_instance

        except ImportError:
            print("❌ Библиотека aiohttp-socks не установлена!")
            print("   Установите: pip install aiohttp-socks")
            break

        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                print(f"   ⏰ Таймаут соединения")
            elif "connection refused" in error_msg.lower():
                print(f"   🔌 Соединение отклонено")
            else:
                print(f"   ❌ Ошибка: {error_msg[:50]}...")

            # Закрываем сессию если была создана
            if 'session' in locals():
                await session.close()

            continue

    # Если ни один прокси не сработал
    if bot_instance is None:
        print("⚠️ ВНИМАНИЕ: Ни один прокси не сработал!")
        print("   Пробуем прямое подключение (требуется VPN)...")
        print("=" * 60)

        # Пробуем создать бота без прокси (требуется VPN)
        try:
            bot_instance = Bot(token=token, parse_mode=ParseMode.HTML)
            me = await bot_instance.get_me(request_timeout=15)
            print(f"✅ Прямое подключение работает (VPN включен)")
            print(f"   🤖 Бот: @{me.username}")
            return bot_instance
        except Exception as e:
            print(f"❌ Прямое подключение тоже не работает: {e}")
            print("   ВКЛЮЧИТЕ VPN и перезапустите бота!")
            raise ConnectionError("Не удалось подключиться к Telegram API")

    return bot_instance


def ensure_data_dir() -> None:
    data_dir = os.path.dirname(settings.database_path)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)


def require_approved(user_id: int) -> bool:
    user = db.get_user(user_id)
    return bool(user and user["status"] == "approved")


def format_leaderboard(category: str, period_label: str, since: Optional[datetime]):
    leaderboard = db.get_leaderboard(category, since)
    lines = [
        f"🏆 Топ по категории {CATEGORY_LABELS.get(category, category)} ({period_label})",
    ]
    if not leaderboard:
        lines.append("Пока никто не оставлял записи. Будьте первым!")
        return "\n".join(lines)
    for idx, row in enumerate(leaderboard, start=1):
        lines.append(f"{idx}. {row['full_name']} ({row['city']}) — {row['total']}")
    return "\n".join(lines)


def format_personal_stats(user_id: int) -> str:
    profile = db.get_profile(user_id)
    if not profile:
        return "Вы еще не зарегистрированы."
    created_at = datetime.fromisoformat(profile["created_at"])
    days_in_bot = (datetime.utcnow() - created_at).days
    last_activity_raw = profile["last_activity_at"]
    last_activity_text = "нет записей" if not last_activity_raw else f"{last_activity_raw}"

    periods = {
        "day": "За 1 день",
        "week": "За неделю",
        "month": "За месяц",
    }
    stats = db.get_personal_all_stats(user_id)
    lines = [
        f"👤 {profile['full_name']}\n📞 {profile['phone']}\n🏙️ {profile['city']}\n🗓️ В боте {days_in_bot} дн.",
        f"⏰ Последняя запись: {last_activity_text}",
        "\n📊 Ваша статистика:",
    ]
    grouped = {(cat, period): total for cat, period, total in stats}
    for period_key, period_label in periods.items():
        lines.append(f"\n{period_label}:")
        for cat_key, cat_label in CATEGORY_LABELS.items():
            total = grouped.get((cat_key, period_key), 0)
            lines.append(f"• {cat_label}: {total}")
    return "\n".join(lines)


async def ensure_access(message: Message, state: FSMContext | None = None) -> bool:
    user = db.get_user(message.from_user.id)
    if not user:
        await send_compact(
            message.bot,
            message.chat.id,
            "Привет! 👋 Сначала нужно зарегистрироваться. Нажми «Регистрация» и заполните данные.",
            reply_markup=REGISTER_BUTTON,
        )
        await try_delete_message(message)
        return False
    status = user["status"]
    if status == "pending":
        await send_compact(
            message.bot,
            message.chat.id,
            "⏳ Заявка на модерации. Админ скоро проверит и даст доступ.",
        )
        await try_delete_message(message)
        return False
    if status == "rejected":
        await send_compact(
            message.bot,
            message.chat.id,
            "🙅‍♂️ Заявка была отклонена. Напишите администратору, если это ошибка.",
        )
        await try_delete_message(message)
        return False
    if status == "banned":
        await send_compact(
            message.bot,
            message.chat.id,
            "🚫 Вы в черном списке бота. Свяжитесь с администратором для разблокировки.",
        )
        await try_delete_message(message)
        if state:
            await state.clear()
        return False
    return True


def period_keyboard(category: str):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = [
        ("🕐 За 1 день", "day"),
        ("📅 За неделю", "week"),
        ("🗓️ За месяц", "month"),
        ("📆 За год", "year"),
        ("♾️ За все время", "all"),
        ("⬅️ Назад", "back:rating"),
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"period:{category}:{key}")]
            if not key.startswith("back")
            else [InlineKeyboardButton(text=label, callback_data=key)]
            for label, key in buttons
        ]
    )


def get_period_label(period_key: str) -> str:
    return {
        "day": "За 1 день",
        "week": "За неделю",
        "month": "За месяц",
        "year": "За год",
        "all": "За все время",
    }.get(period_key, "За период")


def is_admin(user_id: int) -> bool:
    if user_id in settings.admin_ids:
        return True
    user = db.get_user(user_id)
    if user and user["phone"] in settings.admin_phones:
        return True
    return False


def build_users_keyboard(users, action: str) -> InlineKeyboardMarkup:
    rows = []
    for user in users:
        label = f"{'🚫' if action == 'ban' else '♻️'} {user['full_name']} ({user['city']})"
        callback = f"{action}:{user['user_id']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=callback)])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


dp = Dispatcher()
_last_message_ids: Dict[int, int] = {}
BACK_MAIN_INLINE = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")]]
)


async def send_compact(bot: Bot, chat_id: int, text: str, reply_markup=None) -> None:
    message_id = _last_message_ids.get(chat_id)
    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except Exception as exc:
            logger.debug("Не удалось отредактировать сообщение %s: %s", message_id, exc)
    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    _last_message_ids[chat_id] = sent.message_id


async def try_delete_message(message: Message | CallbackQuery) -> None:
    try:
        target = message.message if isinstance(message, CallbackQuery) else message
        await target.delete()
    except Exception as exc:
        logger.debug("Не удалось удалить сообщение: %s", exc)


@dp.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.clear()
    user = db.get_user(message.from_user.id)
    if not user:
        await send_compact(
            message.bot,
            message.chat.id,
            "Привет! 👋 Чтобы пользоваться ботом, нажми \"Регистрация\" и оставь свои данные.",
            reply_markup=REGISTER_BUTTON,
        )
        await try_delete_message(message)
        return
    if user["status"] == "pending":
        await send_compact(
            message.bot,
            message.chat.id,
            "Ваш запрос на регистрацию уже отправлен администратору. Ждите подтверждения."
        )
        await try_delete_message(message)
        return
    if user["status"] == "rejected":
        await send_compact(
            message.bot,
            message.chat.id,
            "К сожалению, ваша регистрация была отклонена. Свяжитесь с администратором, если считаете это ошибкой."
        )
        await try_delete_message(message)
        return
    if user["status"] == "banned":
        await send_compact(
            message.bot,
            message.chat.id,
            "🚫 Ваш профиль занесен в черный список. Напишите администратору, чтобы решить вопрос.",
        )
        await try_delete_message(message)
        return
    await send_compact(
        message.bot,
        message.chat.id,
        "С возвращением! Выберите действие:",
        reply_markup=main_menu(is_admin=is_admin(message.from_user.id)),
    )
    await try_delete_message(message)


@dp.message(F.text == "🚀 Регистрация")
async def start_registration(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RegistrationState.full_name)
    await send_compact(message.bot, message.chat.id, "Введите ваше ФИО полностью:")
    await try_delete_message(message)


@dp.message(RegistrationState.full_name)
async def registration_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(RegistrationState.phone)
    await send_compact(
        message.bot, message.chat.id, "📱 Укажите номер телефона (включая код страны):"
    )
    await try_delete_message(message)


@dp.message(RegistrationState.phone)
async def registration_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(RegistrationState.city)
    await send_compact(message.bot, message.chat.id, "🏙️ В каком городе вы находитесь?")
    await try_delete_message(message)


@dp.message(RegistrationState.city)
async def registration_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await state.set_state(RegistrationState.age)
    await send_compact(message.bot, message.chat.id, "🎂 Сколько вам лет?")
    await try_delete_message(message)


@dp.message(RegistrationState.age)
async def registration_age(message: Message, state: FSMContext, bot: Bot):
    try:
        age = int(message.text.strip())
        if age <= 0:
            raise ValueError
    except ValueError:
        await send_compact(
            bot, message.chat.id, "Возраст должен быть положительным числом. Попробуйте снова."
        )
        await try_delete_message(message)
        return

    data = await state.get_data()
    db.add_user(
        user_id=message.from_user.id,
        full_name=data["full_name"],
        phone=data["phone"],
        city=data["city"],
        age=age,
    )
    await state.clear()
    await send_compact(
        bot,
        message.chat.id,
        "Спасибо! Ваши данные отправлены администратору. Мы сообщим, как только он одобрит запрос.",
    )
    await try_delete_message(message)

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                (
                    "Новая заявка на регистрацию:\n"
                    f"👤 {data['full_name']}\n"
                    f"📞 {data['phone']}\n"
                    f"🏙️ {data['city']}\n"
                    f"🎂 {age} лет"
                ),
                reply_markup=approval_keyboard(message.from_user.id),
            )
        except Exception as exc:
            logger.error("Не удалось отправить уведомление админу %s: %s", admin_id, exc)


@dp.callback_query(F.data.startswith("approve:"))
async def approve_user(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    db.set_user_status(user_id, "approved")
    await callback.answer("Пользователь одобрен")
    try:
        await send_compact(
            bot,
            user_id,
            "Ура! 🎉 Ваша регистрация одобрена. Можете пользоваться ботом.",
            reply_markup=main_menu(is_admin=is_admin(user_id)),
        )
    except Exception as exc:
        logger.error("Не удалось отправить сообщение пользователю %s: %s", user_id, exc)


@dp.callback_query(F.data.startswith("reject:"))
async def reject_user(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    db.set_user_status(user_id, "rejected")
    await callback.answer("Пользователь отклонен")
    try:
        await send_compact(
            bot,
            user_id,
            "К сожалению, ваша заявка отклонена. Свяжитесь с администратором, чтобы узнать детали.",
        )
    except Exception as exc:
        logger.error("Не удалось отправить сообщение пользователю %s: %s", user_id, exc)


@dp.message(F.text == "✍️ Записать")
async def choose_activity(message: Message, state: FSMContext):
    if not await ensure_access(message, state):
        return
    await state.set_state(ActivityState.category)
    await send_compact(
        message.bot,
        message.chat.id,
        "Выберите, что хотите записать:",
        reply_markup=ACTIVITY_CHOICES,
    )
    await try_delete_message(message)


@dp.callback_query(ActivityState.category, F.data.startswith("activity:"))
async def activity_selected(callback: CallbackQuery, state: FSMContext):
    _, category = callback.data.split(":", maxsplit=1)
    await state.update_data(category=category)
    await state.set_state(ActivityState.value)
    await send_compact(
        callback.message.bot,
        callback.message.chat.id,
        f"Сколько \"{CATEGORY_LABELS.get(category, category)}\" добавить? Введите число.",
    )
    await callback.answer()


@dp.message(ActivityState.value)
async def activity_value(message: Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("category")
    try:
        value = float(message.text.replace(",", "."))
        if value <= 0:
            raise ValueError
    except ValueError:
        await send_compact(message.bot, message.chat.id, "Введите положительное число.")
        await try_delete_message(message)
        return
    db.add_activity(message.from_user.id, category, value)
    await state.clear()
    await send_compact(
        message.bot,
        message.chat.id,
        f"Записано! {CATEGORY_LABELS.get(category, category)}: {value}",
        reply_markup=main_menu(is_admin=is_admin(message.from_user.id)),
    )
    await try_delete_message(message)


@dp.message(F.text == "🏆 Рейтинг")
async def rating_menu(message: Message, state: FSMContext):
    if not await ensure_access(message, state):
        return
    await state.clear()
    await state.set_state(RatingState.category)
    await send_compact(
        message.bot, message.chat.id, "Выберите категорию рейтинга:", reply_markup=RATING_MENU
    )
    await try_delete_message(message)


@dp.callback_query(RatingState.category, F.data.startswith("rating:"))
async def rating_category(callback: CallbackQuery, state: FSMContext):
    _, category = callback.data.split(":", maxsplit=1)
    await state.update_data(category=category)
    await send_compact(
        callback.message.bot,
        callback.message.chat.id,
        f"Показываю рейтинги для \"{CATEGORY_LABELS.get(category, category)}\". Выберите период:",
        reply_markup=period_keyboard(category),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("period:"))
async def rating_period(callback: CallbackQuery, state: FSMContext):
    _, category, period_key = callback.data.split(":")
    since = db.format_period(period_key)
    text = format_leaderboard(category, get_period_label(period_key), since)
    await send_compact(callback.message.bot, callback.message.chat.id, text)
    await callback.answer()
    await state.clear()


@dp.callback_query(F.data == "back:rating")
async def back_to_rating(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RatingState.category)
    await send_compact(
        callback.message.bot,
        callback.message.chat.id,
        "Выберите категорию рейтинга:",
        reply_markup=RATING_MENU,
    )
    await callback.answer()


@dp.callback_query(F.data == "back:main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_compact(
        callback.message.bot,
        callback.message.chat.id,
        "Главное меню:",
        reply_markup=main_menu(is_admin=is_admin(callback.from_user.id)),
    )
    await callback.answer()


@dp.message(F.text == "ℹ️ О себе")
async def about_me(message: Message):
    if not await ensure_access(message):
        return
    await send_compact(message.bot, message.chat.id, format_personal_stats(message.from_user.id))
    await try_delete_message(message)


@dp.message(F.text == "📢 Рассылка")
async def start_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await send_compact(message.bot, message.chat.id, "Эта функция доступна только администратору.")
        return
    await state.set_state(BroadcastState.waiting_for_message)
    await send_compact(
        message.bot,
        message.chat.id,
        "Введите текст рассылки. Он уйдет всем одобренным пользователям:",
    )
    await try_delete_message(message)


@dp.message(BroadcastState.waiting_for_message)
async def send_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        await send_compact(message.bot, message.chat.id, "Эта функция доступна только администратору.")
        await state.clear()
        return
    text = message.text
    sent = 0
    failed = 0
    for user_id in db.get_registered_users(["approved"]):
        try:
            await bot.send_message(user_id, f"📢 Сообщение от админа:\n{text}")
            sent += 1
        except Exception as exc:
            failed += 1
            logger.error("Не удалось отправить рассылку %s: %s", user_id, exc)
    await send_compact(
        message.bot,
        message.chat.id,
        f"Готово! Успешно: {sent}. Не доставлено: {failed}.",
        reply_markup=main_menu(is_admin=True),
    )
    await state.clear()
    await try_delete_message(message)


def format_users_block(title: str, users: list) -> str:
    lines = [title]
    if not users:
        lines.append("Пока пусто ✨")
    else:
        for idx, user in enumerate(users, start=1):
            lines.append(
                f"{idx}. {user['full_name']} — {user['phone']} ({user['city']}), {user['age']} лет"
            )
    return "\n".join(lines)


@dp.message(F.text == "👥 Участники")
async def list_participants(message: Message):
    if not is_admin(message.from_user.id):
        await send_compact(message.bot, message.chat.id, "Эта функция доступна только администратору.")
        return
    all_users = db.list_users_by_status(["approved", "pending"])
    users = all_users[:25]
    note = "" if len(all_users) <= len(users) else "\nПоказаны первые 25 записей."
    text = format_users_block("👥 Участники (одобренные и на проверке)", users) + note
    keyboard = build_users_keyboard(users, "ban") if users else BACK_MAIN_INLINE
    await send_compact(message.bot, message.chat.id, text, reply_markup=keyboard)
    await try_delete_message(message)


@dp.message(F.text == "🚫 Черный список")
async def list_blacklist(message: Message):
    if not is_admin(message.from_user.id):
        await send_compact(message.bot, message.chat.id, "Эта функция доступна только администратору.")
        return
    all_users = db.list_users_by_status(["banned"])
    users = all_users[:25]
    note = "" if len(all_users) <= len(users) else "\nПоказаны первые 25 записей."
    text = format_users_block("🚫 Черный список", users) + note
    keyboard = build_users_keyboard(users, "unban") if users else BACK_MAIN_INLINE
    await send_compact(message.bot, message.chat.id, text, reply_markup=keyboard)
    await try_delete_message(message)


@dp.callback_query(F.data.startswith("ban:"))
async def ban_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    db.set_user_status(user_id, "banned")
    await callback.answer("Пользователь занесен в черный список")
    await send_compact(
        callback.message.bot,
        callback.message.chat.id,
        "🚫 Пользователь добавлен в черный список.",
        reply_markup=main_menu(is_admin=True),
    )
    try:
        await send_compact(
            callback.message.bot,
            user_id,
            "🚫 Вы добавлены в черный список. Свяжитесь с администратором для разблокировки.",
        )
    except Exception as exc:
        logger.debug("Не удалось уведомить заблокированного пользователя %s: %s", user_id, exc)


@dp.callback_query(F.data.startswith("unban:"))
async def unban_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    db.set_user_status(user_id, "approved")
    await callback.answer("Пользователь разбанен")
    await send_compact(
        callback.message.bot,
        callback.message.chat.id,
        "✅ Пользователь разблокирован и возвращен в список одобренных.",
        reply_markup=main_menu(is_admin=True),
    )
    try:
        await send_compact(
            callback.message.bot,
            user_id,
            "✅ Вы разблокированы! Доступ к боту восстановлен.",
            reply_markup=main_menu(is_admin=is_admin(user_id)),
        )
    except Exception as exc:
        logger.debug("Не удалось уведомить разблокированного пользователя %s: %s", user_id, exc)


async def main() -> None:
    # Проверяем наличие библиотеки для прокси
    try:
        import aiohttp_socks
        print("✅ Библиотека aiohttp-socks установлена")
    except ImportError:
        print("⚠️ Установите библиотеку для прокси: pip install aiohttp-socks")

    ensure_data_dir()
    db.init_db()

    if not settings.bot_token:
        raise RuntimeError("Не указан токен бота.")

    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК ФИТНЕС-ТРЕКЕР БОТА")
    print("=" * 60)

    try:
        # Создаем бота с автоматическим подбором прокси
        bot = await create_bot_with_proxy(settings.bot_token)

        # Пропускаем проверку вебхука (для России)
        print("⏩ Пропускаем проверку вебхука (оптимизация для РФ)")

        print("=" * 60)
        print("✅ БОТ УСПЕШНО ЗАПУЩЕН!")
        print("=" * 60)
        print("📱 Откройте Telegram и найдите вашего бота")
        print("💬 Напишите команду /start")
        print("=" * 60)
        print("Для остановки нажмите Ctrl+C")
        print("=" * 60 + "\n")

        # Запускаем polling
        await dp.start_polling(bot, skip_updates=True)

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print("\n🔧 РЕШЕНИЯ:")
        print("1. ВКЛЮЧИТЕ VPN (обязательно для России)")
        print("2. Проверьте токен бота в @BotFather")
        print("3. Установите библиотеку: pip install aiohttp-socks")
        print("4. Перезапустите бота")


if __name__ == "__main__":
    # Подавляем предупреждения
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")