# epicservice/handlers/common.py

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from config import ADMIN_IDS, WEBAPP_URL
from database.orm import orm_upsert_user
from keyboards.inline import get_admin_main_kb
from lexicon.lexicon import LEXICON

logger = logging.getLogger(__name__)

router = Router()


async def clean_previous_keyboard(state: FSMContext, bot: Bot, chat_id: int):
    """
    Видаляє інлайн-клавіатуру з попереднього головного повідомлення.
    Використовується адмін-хендлерами для очищення inline-клавіатур.
    """
    data = await state.get_data()
    previous_message_id = data.get("main_message_id")
    if previous_message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=previous_message_id,
                reply_markup=None
            )
        except TelegramBadRequest as e:
            # Типова ситуація: повідомлення вже видалено або не змінилось
            logger.debug("clean_previous_keyboard: не вдалося видалити клавіатуру (msg_id=%s): %s",
                         previous_message_id, e)


def get_user_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавіатура для звичайних користувачів: тільки кнопка Mini App.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌐 Відкрити Mini App", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавіатура для адмінів: Mini App + кнопка Адмінка.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌐 Відкрити Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="⚙️ Адмінка")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """
    Обробник команди /start.
    Реєструє користувача та показує персистентну клавіатуру:
    - Для користувачів: кнопка Mini App
    - Для адмінів: Mini App + Адмінка
    """
    user = message.from_user
    try:
        # Реєструємо користувача в БД
        await orm_upsert_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        logger.info("Команда /start від користувача %s.", user.id)

        # Очищаємо FSM state
        await state.clear()

        # Визначаємо текст та клавіатуру залежно від ролі
        if user.id in ADMIN_IDS:
            text = LEXICON.CMD_START_ADMIN
            kb = get_admin_keyboard()
        else:
            text = LEXICON.CMD_START_USER
            kb = get_user_keyboard()

        # Надсилаємо привітання з персистентною клавіатурою
        await message.answer(text, reply_markup=kb)

    except Exception as e:
        logger.error("Неочікувана помилка в cmd_start для %s: %s", user.id, e, exc_info=True)
        await message.answer(LEXICON.UNEXPECTED_ERROR)


@router.message(F.text == "⚙️ Адмінка")
async def admin_button_handler(message: Message):
    """
    Обробник натискання кнопки "Адмінка".
    Показує inline-меню з адміністративними функціями.
    """
    user_id = message.from_user.id
    
    # Перевірка чи юзер є адміном
    if user_id not in ADMIN_IDS:
        await message.answer("❌ У вас немає доступу до адміністративних функцій.")
        return
    
    # Показуємо inline-меню (існуюча адмінська клавіатура)
    await message.answer(
        "⚙️ *Панель адміністратора*\n\nОберіть дію:",
        reply_markup=get_admin_main_kb()
    )
