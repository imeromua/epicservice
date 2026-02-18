# epicservice/handlers/user/list_management.py

import logging
import os

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)
from sqlalchemy.exc import SQLAlchemyError

from config import ADMIN_IDS
from database.engine import async_session
from database.orm import orm_clear_temp_list, orm_get_temp_list
from handlers.common import clean_previous_keyboard
from keyboards.inline import (get_admin_main_kb, get_confirmation_kb,
                              get_my_list_kb, get_user_main_kb)
from lexicon.lexicon import LEXICON
from utils.list_processor import process_and_save_list

logger = logging.getLogger(__name__)
router = Router()


class ListManagementStates(StatesGroup):
    confirm_new_list = State()
    confirm_cancel_list = State()
    confirm_save_list = State()


async def _display_user_list(bot: Bot, chat_id: int, user_id: int, state: FSMContext):
    """
    Відображає поточний список користувача, оновлюючи ID головного повідомлення.
    """
    try:
        temp_list = await orm_get_temp_list(user_id)
        if not temp_list:
            back_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=LEXICON.BUTTON_BACK_TO_MAIN_MENU,
                    callback_data="main:back"
                )
            ]])
            sent_message = await bot.send_message(chat_id, LEXICON.EMPTY_LIST, reply_markup=back_kb)
            await state.update_data(main_message_id=sent_message.message_id)
            return

        department_id = temp_list[0].product.відділ
        header = [f"*Ваш поточний список (Відділ: {department_id}):*"]
        list_items = [f"`{item.product.артикул}` - *{item.quantity}* шт." for item in temp_list]

        MAX_TELEGRAM_MESSAGE_LENGTH = 4096
        parts, current_part = [], "\n".join(header)

        for line in list_items:
            if len(current_part) + len(line) + 1 > MAX_TELEGRAM_MESSAGE_LENGTH:
                parts.append(current_part)
                current_part = line
            else:
                current_part += "\n" + line
        parts.append(current_part)

        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                sent_message = await bot.send_message(chat_id, part, reply_markup=get_my_list_kb())
                await state.update_data(main_message_id=sent_message.message_id)
            else:
                await bot.send_message(chat_id, part)
    except Exception as e:
        logger.error("Помилка відображення списку для %s: %s", user_id, e, exc_info=True)
        await bot.send_message(chat_id, LEXICON.UNEXPECTED_ERROR)


@router.callback_query(F.data == "main:back")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """
    Повертає користувача на головне меню, редагуючи поточне повідомлення.
    """
    user_id = callback.from_user.id
    kb = get_admin_main_kb() if user_id in ADMIN_IDS else get_user_main_kb()
    text = LEXICON.CMD_START_ADMIN if user_id in ADMIN_IDS else LEXICON.CMD_START_USER
    try:
        await callback.message.edit_text(text, reply_markup=kb)
        await state.update_data(main_message_id=callback.message.message_id)
    except TelegramBadRequest:
        await clean_previous_keyboard(state, callback.bot, callback.message.chat.id)
        sent_message = await callback.message.answer(text, reply_markup=kb)
        await state.update_data(main_message_id=sent_message.message_id)
    finally:
        await callback.answer()


@router.callback_query(F.data == "main:new_list")
async def new_list_handler(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text(
            LEXICON.NEW_LIST_CONFIRM,
            reply_markup=get_confirmation_kb("confirm_new_list", "main:back"),
        )
        await state.set_state(ListManagementStates.confirm_new_list)
    except TelegramBadRequest as e:
        logger.warning("Помилка редагування повідомлення при запиті нового списку: %s", e)
    finally:
        await callback.answer()


@router.callback_query(ListManagementStates.confirm_new_list, F.data == "confirm_new_list")
async def new_list_confirmed(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(None)
    try:
        await orm_clear_temp_list(user_id)
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=LEXICON.BUTTON_BACK_TO_MAIN_MENU,
                callback_data="main:back"
            )
        ]])
        await callback.message.edit_text(
            LEXICON.NEW_LIST_CONFIRMED,
            reply_markup=back_kb
        )
        await state.update_data(main_message_id=callback.message.message_id)
    except SQLAlchemyError as e:
        logger.error("Помилка БД при очищенні тимчасового списку для %s: %s", user_id, e, exc_info=True)
        await callback.message.edit_text(LEXICON.UNEXPECTED_ERROR)
    finally:
        await callback.answer()


@router.callback_query(F.data == "main:my_list")
async def my_list_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """
    Обробляє запит "Мій список", видаляючи клавіатуру з попереднього меню.
    """
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as e:
        logger.debug("my_list_handler: не вдалося прибрати клавіатуру: %s", e)
    await _display_user_list(bot, callback.message.chat.id, callback.from_user.id, state)
    await callback.answer()


@router.callback_query(F.data == "save_list:confirm")
async def save_list_handler(callback: CallbackQuery, state: FSMContext):
    """
    Просить підтвердження збереження списку.
    """
    await callback.message.edit_text(
        LEXICON.SAVE_LIST_CONFIRM,
        reply_markup=get_confirmation_kb("save_list:yes", "save_list:no")
    )
    await state.set_state(ListManagementStates.confirm_save_list)
    await callback.answer()


@router.callback_query(ListManagementStates.confirm_save_list, F.data == "save_list:yes")
async def save_list_confirmed(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Зберігає список в БД та відправляє Excel файл.
    """
    user_id = callback.from_user.id
    await state.set_state(None)
    
    try:
        # Прибираємо клавіатуру з підтвердження
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest as e:
            logger.debug("save_list_confirmed: не вдалося прибрати клавіатуру: %s", e)
        
        # Відправляємо повідомлення "Обробка..."
        processing_msg = await callback.message.answer("⌛️ Обробка списку...")
        
        # Обробляємо та зберігаємо список в єдиній транзакції
        async with async_session() as session:
            async with session.begin():
                main_list_path, surplus_list_path = await process_and_save_list(session, user_id)
        
        # Видаляємо повідомлення "Обробка..."
        try:
            await bot.delete_message(callback.message.chat.id, processing_msg.message_id)
        except TelegramBadRequest:
            pass
        
        if main_list_path:
            # Відправляємо основний файл
            if os.path.exists(main_list_path):
                await callback.message.answer_document(
                    FSInputFile(main_list_path),
                    caption="✅ Список успішно збережено!"
                )
            
            # Відправляємо файл лишків (якщо є)
            if surplus_list_path and os.path.exists(surplus_list_path):
                await callback.message.answer_document(
                    FSInputFile(surplus_list_path),
                    caption="⚠️ Лишки (товари, яких не вистачило на складі)"
                )
            
            logger.info("Список user_id=%s успішно збережено: %s", user_id, main_list_path)
        else:
            await callback.message.answer("❌ Помилка збереження списку.")
            logger.error("Помилка збереження списку user_id=%s: main_list_path порожній", user_id)
        
        # Повертаємось до головного меню
        user = callback.from_user
        kb = get_admin_main_kb() if user.id in ADMIN_IDS else get_user_main_kb()
        text = LEXICON.CMD_START_ADMIN if user.id in ADMIN_IDS else LEXICON.CMD_START_USER
        sent_message = await callback.message.answer(text, reply_markup=kb)
        await state.update_data(main_message_id=sent_message.message_id)
        
    except Exception as e:
        logger.error("Помилка при збереженні списку user_id=%s: %s", user_id, e, exc_info=True)
        await callback.message.answer(LEXICON.UNEXPECTED_ERROR)
    finally:
        await callback.answer()


@router.callback_query(ListManagementStates.confirm_save_list, F.data == "save_list:no")
async def save_list_declined(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Скасування збереження списку.
    """
    await state.set_state(None)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as e:
        logger.debug("save_list_declined: не вдалося прибрати клавіатуру: %s", e)
    await _display_user_list(bot, callback.message.chat.id, callback.from_user.id, state)
    await callback.answer()


@router.callback_query(F.data == "cancel_list:confirm")
async def cancel_list_confirm_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        LEXICON.CANCEL_LIST_CONFIRM,
        reply_markup=get_confirmation_kb("cancel_list:yes", "cancel_list:no")
    )
    await state.set_state(ListManagementStates.confirm_cancel_list)
    await callback.answer()


@router.callback_query(ListManagementStates.confirm_cancel_list, F.data == "cancel_list:yes")
async def cancel_list_confirmed(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    await state.set_state(None)
    try:
        await orm_clear_temp_list(user_id)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest as e:
            logger.debug("cancel_list_confirmed: не вдалося прибрати клавіатуру: %s", e)
        await callback.message.answer(LEXICON.LIST_CANCELED)

        user = callback.from_user
        kb = get_admin_main_kb() if user.id in ADMIN_IDS else get_user_main_kb()
        text = LEXICON.CMD_START_ADMIN if user.id in ADMIN_IDS else LEXICON.CMD_START_USER

        sent_message = await callback.message.answer(text, reply_markup=kb)
        await state.update_data(main_message_id=sent_message.message_id)

    except SQLAlchemyError as e:
        logger.error("Помилка БД при скасуванні списку для %s: %s", user_id, e, exc_info=True)
        await callback.message.edit_text(LEXICON.UNEXPECTED_ERROR)
    finally:
        await callback.answer()


@router.callback_query(ListManagementStates.confirm_cancel_list, F.data == "cancel_list:no")
async def cancel_list_declined(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(None)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as e:
        logger.debug("cancel_list_declined: не вдалося прибрати клавіатуру: %s", e)
    await _display_user_list(bot, callback.message.chat.id, callback.from_user.id, state)
    await callback.answer()
