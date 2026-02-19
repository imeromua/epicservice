# epicservice/handlers/common.py

import logging

from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from config import ADMIN_IDS, WEBAPP_URL
from database.orm import orm_upsert_user
from lexicon.lexicon import LEXICON

logger = logging.getLogger(__name__)

router = Router()


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
