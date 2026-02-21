# epicservice/handlers/common.py

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.types import ReplyKeyboardRemove

from config import WEBAPP_URL
from database.orm import orm_upsert_user
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


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """
    Обробник команди /start.
    Реєструє користувача та відкриває Mini App.
    Тільки одна кнопка: "Відкрити EpicService".
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

        # Прибираємо всі reply-клавіатури
        await message.answer(
            "👋",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Надсилаємо ТІЛЬКИ кнопку Mini App
        mini_app_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Відкрити EpicService", web_app=WebAppInfo(url=WEBAPP_URL))]
            ]
        )
        
        await message.answer(
            "🚀 *Ласкаво просимо!*",
            reply_markup=mini_app_kb,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error("Неочікувана помилка в cmd_start для %s: %s", user.id, e, exc_info=True)
        await message.answer(LEXICON.UNEXPECTED_ERROR)
