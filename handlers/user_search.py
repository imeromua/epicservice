# epicservice/handlers/user_search.py

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import SQLAlchemyError

from database.engine import async_session
from database.orm import (orm_find_products, orm_get_product_by_id, 
                          orm_add_item_to_temp_list, orm_get_temp_list_department,
                          orm_delete_temp_list_item, orm_update_temp_list_item_quantity) 
from handlers.common import clean_previous_keyboard
from handlers.user.list_management import back_to_main_menu
from keyboards.inline import get_search_results_kb, get_product_card_kb
from lexicon.lexicon import LEXICON
from utils.card_generator import send_or_edit_product_card

logger = logging.getLogger(__name__)
router = Router()

class SearchStates(StatesGroup):
    showing_results = State()
    waiting_for_manual_quantity = State() 


@router.message(F.text)
async def search_handler(message: Message, bot: Bot, state: FSMContext):
    """
    Обробник пошуку.
    """
    current_state = await state.get_state()
    if current_state != SearchStates.waiting_for_manual_quantity:
         await state.set_state(None)
    
    search_query = message.text
    
    known_commands = {
        LEXICON.BUTTON_NEW_LIST, LEXICON.BUTTON_MY_LIST,
        LEXICON.BUTTON_ARCHIVE, LEXICON.BUTTON_ADMIN_PANEL,
    }
    if search_query.startswith("/") or search_query in known_commands:
        return

    try:
        await message.delete()
    except TelegramBadRequest:
        logger.warning("Не вдалося видалити пошуковий запит користувача.")

    if len(search_query) < 3:
        await message.answer(LEXICON.SEARCH_TOO_SHORT, reply_markup=None)
        return
        
    try:
        await clean_previous_keyboard(state, bot, message.chat.id)

        products = await orm_find_products(search_query)
        if not products:
            sent_message = await message.answer(LEXICON.SEARCH_NO_RESULTS, reply_markup=None)
            await state.update_data(main_message_id=sent_message.message_id)
            return
            
        if len(products) == 1:
            # При першому показі current_selection=1 (default)
            sent_message = await send_or_edit_product_card(bot, message.chat.id, message.from_user.id, products[0])
            if sent_message:
                await state.update_data(main_message_id=sent_message.message_id)
        else:
            await state.set_state(SearchStates.showing_results)
            await state.update_data(last_query=search_query)
            
            sent_message = await message.answer(
                LEXICON.SEARCH_MANY_RESULTS, 
                reply_markup=get_search_results_kb(products)
            )
            await state.update_data(main_message_id=sent_message.message_id)
            
    except SQLAlchemyError as e:
        logger.error("Помилка пошуку товарів для запиту '%s': %s", search_query, e)
        await message.answer(LEXICON.UNEXPECTED_ERROR)


@router.callback_query(F.data.startswith("product:"))
async def show_product_from_button(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    try:
        product_id = int(callback.data.split(":", 1)[1])
        
        fsm_data = await state.get_data()
        last_query = fsm_data.get('last_query')
        
        async with async_session() as session:
            product = await orm_get_product_by_id(session, product_id)
            if product:
                sent_message = await send_or_edit_product_card(
                    bot=bot, 
                    chat_id=callback.message.chat.id, 
                    user_id=callback.from_user.id, 
                    product=product,
                    message_id=callback.message.message_id, 
                    search_query=last_query
                )
                if sent_message:
                    await state.update_data(main_message_id=sent_message.message_id)
            else:
                await callback.message.edit_text(LEXICON.PRODUCT_NOT_FOUND)
                
    except (ValueError, IndexError, SQLAlchemyError) as e:
        logger.error("Помилка БД при отриманні товару: %s", e)
        await callback.message.edit_text(LEXICON.UNEXPECTED_ERROR)


@router.callback_query(SearchStates.showing_results, F.data == "back_to_results")
async def back_to_results_handler(callback: CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    last_query = fsm_data.get('last_query')

    if not last_query:
        await back_to_main_menu(callback, state)
        await callback.answer("Помилка: запит не знайдено", show_alert=True)
        return

    products = await orm_find_products(last_query)
    
    await callback.message.edit_text(
        LEXICON.SEARCH_MANY_RESULTS,
        reply_markup=get_search_results_kb(products)
    )
    await state.update_data(main_message_id=callback.message.message_id)
    await callback.answer()


@router.callback_query(F.data.startswith("selector:"))
async def handle_selector_change(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """
    Обробка кнопок +/- на картці товару (Selector Mode).
    ТІЛЬКИ оновлює клавіатуру, не чіпає БД.
    """
    # Format: selector:action:product_id:current_val:max_val
    try:
        parts = callback.data.split(":")
        action = parts[1]
        product_id = int(parts[2])
        current_val = int(parts[3])
        max_val = int(parts[4])
        
        user_id = callback.from_user.id
        
        new_val = current_val
        if action == "inc":
            if current_val < max_val:
                new_val += 1
            else:
                await callback.answer(f"Максимально доступно: {max_val}", show_alert=True)
                return
        elif action == "dec":
            if current_val > 1:
                new_val -= 1
            else:
                await callback.answer("Мінімум 1 шт.", show_alert=False)
                return
        
        if new_val != current_val:
            # Оновлюємо ТІЛЬКИ КЛАВІАТУРУ (перемальовуємо картку з новим selection)
            async with async_session() as session:
                product = await orm_get_product_by_id(session, product_id)
                if product:
                     data = await state.get_data()
                     last_query = data.get('last_query')
                     
                     await send_or_edit_product_card(
                        bot=bot,
                        chat_id=callback.message.chat.id,
                        user_id=user_id,
                        product=product,
                        message_id=callback.message.message_id,
                        search_query=last_query,
                        current_selection=new_val # Передаємо нове значення селектора
                    )
            
            await callback.answer() # Silent update
        else:
            await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling selector change: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.callback_query(F.data.startswith("add_to_list:"))
async def handle_add_to_list(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """
    Фінальне додавання товару в БД (кнопка 'Додати до списку' або 'Додати все').
    """
    # Format: add_to_list:product_id:quantity
    try:
        parts = callback.data.split(":")
        product_id = int(parts[1])
        quantity_to_add = int(parts[2])
        
        user_id = callback.from_user.id
        
        async with async_session() as session:
             product = await orm_get_product_by_id(session, product_id)
             if not product:
                 await callback.answer(LEXICON.PRODUCT_NOT_FOUND, show_alert=True)
                 return
             
             allowed_department = await orm_get_temp_list_department(user_id)
             if allowed_department is not None and product.відділ != allowed_department:
                await callback.answer(
                    LEXICON.DEPARTMENT_MISMATCH.format(department=allowed_department), 
                    show_alert=True
                )
                return

             # Додаємо в БД
             if quantity_to_add > 0:
                 await orm_add_item_to_temp_list(user_id, product_id, quantity_to_add)
                 
                 # Оновлюємо картку
                 # Після успішного додавання скидаємо селектор на 1 (або 0, якщо ліміт вичерпано, це зробить card_generator)
                 data = await state.get_data()
                 last_query = data.get('last_query')
                 
                 await send_or_edit_product_card(
                    bot=bot,
                    chat_id=callback.message.chat.id,
                    user_id=user_id,
                    product=product,
                    message_id=callback.message.message_id,
                    search_query=last_query,
                    current_selection=1 # Reset to 1
                )
                 
                 await callback.answer(f"✅ Додано {quantity_to_add} шт.", show_alert=True)
             else:
                 await callback.answer("Кількість 0?", show_alert=True)

    except Exception as e:
        logger.error(f"Error handling add to list: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.callback_query(F.data.startswith("qty_manual_input:"))
async def manual_input_callback(callback: CallbackQuery, state: FSMContext):
    """Запитує у користувача кількість для ручного вводу."""
    try:
        product_id = int(callback.data.split(":")[1])
        await state.set_state(SearchStates.waiting_for_manual_quantity)
        await state.update_data(product_id=product_id, message_id=callback.message.message_id)
        
        await callback.message.answer("⌨️ Введіть кількість для додавання:")
        await callback.answer()
    except (ValueError, IndexError) as e:
        logger.error("Помилка обробки callback 'qty_manual_input': %s", e, exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.message(SearchStates.waiting_for_manual_quantity, F.text.isdigit())
async def process_manual_quantity(message: Message, state: FSMContext, bot: Bot):
    """Обробляє кількість, введену вручну (Selector Mode - просто оновлює клавіатуру)."""
    user_id = message.from_user.id
    state_data = await state.get_data()
    product_id = state_data.get("product_id")
    original_message_id = state_data.get("message_id")
    
    # Видаляємо повідомлення користувача з числом
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    
    try:
        quantity = int(message.text)
        if quantity <= 0:
             await message.answer("❌ Кількість має бути більше 0.")
             return

        async with async_session() as session:
             product = await orm_get_product_by_id(session, product_id)
             if not product:
                 await message.answer(LEXICON.PRODUCT_NOT_FOUND)
                 await state.set_state(None)
                 return

             # Оновлюємо картку з НОВИМ current_selection = quantity
             # Не додаємо в БД!
             data = await state.get_data()
             last_query = data.get('last_query')
             
             await send_or_edit_product_card(
                bot=bot,
                chat_id=message.chat.id,
                user_id=user_id,
                product=product,
                message_id=original_message_id,
                search_query=last_query,
                current_selection=quantity
            )
             
             # await message.answer(f"✅ Обрано: {quantity} шт. Натисніть 'Додати'.", show_alert=True)
             
    except Exception as e:
        logger.error("Помилка обробки ручного вводу кількості: %s", e, exc_info=True)
        await message.answer(LEXICON.UNEXPECTED_ERROR)
    
    await state.set_state(None)
