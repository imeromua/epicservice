# epicservice/handlers/common.py

import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from config import ADMIN_IDS
from database.orm import orm_upsert_user
from keyboards.inline import get_admin_main_kb, get_user_main_kb
from lexicon.lexicon import LEXICON

logger = logging.getLogger(__name__)

router = Router()


async def clean_previous_keyboard(state: FSMContext, bot: Bot, chat_id: int):
    """
    Видаляє інлайн-клавіатуру з попереднього головного повідомлення.
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
    Видаляє клавіатуру з попереднього повідомлення, реєструє користувача,
    надсилає нове головне меню.
    """
    user = message.from_user
    try:
        await clean_previous_keyboard(state, bot, message.chat.id)

        await orm_upsert_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        logger.info("Команда /start від користувача %s.", user.id)

        if user.id in ADMIN_IDS:
            text = LEXICON.CMD_START_ADMIN
            kb = get_admin_main_kb()
        else:
            text = LEXICON.CMD_START_USER
            kb = get_user_main_kb()

        # Примусово прибираємо Reply-клавіатуру (якщо є) — надсилаємо та одразу видаляємо тимчасове повідомлення
        msg_to_remove_kb = await message.answer("...", reply_markup=ReplyKeyboardRemove())
        await msg_to_remove_kb.delete()

        sent_message = await message.answer(text, reply_markup=kb)
        await state.update_data(main_message_id=sent_message.message_id)

    except Exception as e:
        logger.error("Неочікувана помилка в cmd_start для %s: %s", user.id, e, exc_info=True)
        await message.answer(LEXICON.UNEXPECTED_ERROR)
