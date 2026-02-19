# epicservice/handlers/common.py

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.types import ReplyKeyboardRemove

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


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """
    Обробник команди /start.
    Реєструє користувача та автоматично відкриває Mini App.
    Усі клавіатури прибрані - управління тільки через webapp.
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

        # Визначаємо текст та inline-клавіатуру залежно від ролі
        if user.id in ADMIN_IDS:
            text = (
                f"{LEXICON.CMD_START_ADMIN}\n\n"
                "👉 Натисніть кнопку нижче, щоб відкрити додаток."
            )
            # Адмінська кнопка: Mini App + Адмінка
            inline_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🌐 Відкрити Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
                    [InlineKeyboardButton(text="⚙️ Адмінка", callback_data="admin_panel")]
                ]
            )
        else:
            text = (
                f"{LEXICON.CMD_START_USER}\n\n"
                "👉 Натисніть кнопку нижче, щоб відкрити додаток."
            )
            # Кнопка для користувача: тільки Mini App
            inline_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🌐 Відкрити Mini App", web_app=WebAppInfo(url=WEBAPP_URL))]
                ]
            )

        # Прибираємо всі reply-клавіатури та надсилаємо інлайн
        await message.answer(
            text,
            reply_markup=ReplyKeyboardRemove()  # Видаляємо reply-клавіатуру
        )
        
        # Надсилаємо inline-клавіатуру
        await message.answer(
            "🚀 *Ласкаво просимо до EpicService!*",
            reply_markup=inline_kb
        )

    except Exception as e:
        logger.error("Неочікувана помилка в cmd_start для %s: %s", user.id, e, exc_info=True)
        await message.answer(LEXICON.UNEXPECTED_ERROR)


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback):
    """
    Обробник callback кнопки "Адмінка".
    Показує inline-меню з адміністративними функціями.
    """
    user_id = callback.from_user.id
    
    # Перевірка чи юзер є адміном
    if user_id not in ADMIN_IDS:
        await callback.answer("❌ У вас немає доступу до адміністративних функцій.", show_alert=True)
        return
    
    # Показуємо inline-меню (існуюча адмінська клавіатура)
    await callback.message.answer(
        "⚙️ *Панель адміністратора*\n\nОберіть дію:",
        reply_markup=get_admin_main_kb()
    )
    await callback.answer()
