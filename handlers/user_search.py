# epicservice/handlers/user_search.py

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.exc import SQLAlchemyError

from database.engine import async_session
from database.orm import orm_find_products, orm_get_product_by_id, orm_add_item_to_temp_list
from handlers.common import clean_previous_keyboard
from handlers.user.list_management import back_to_main_menu
from keyboards.inline import get_search_results_kb, get_product_card_kb
from lexicon.lexicon import LEXICON
from utils.card_generator import send_or_edit_product_card

logger = logging.getLogger(__name__)
router = Router()

class SearchStates(StatesGroup):
    showing_results = State()


@router.message(F.text)
async def search_handler(message: Message, bot: Bot, state: FSMContext):
    """
    Обробник пошуку. Тепер видаляє клавіатуру з попереднього меню.
    """
    # Не скидаємо стан повністю, щоб зберегти main_message_id
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
        # Це тимчасове повідомлення, воно не повинно мати клавіатури
        await message.answer(LEXICON.SEARCH_TOO_SHORT, reply_markup=None)
        return
        
    try:
        # --- ОНОВЛЕНА ЛОГІКА: Прибираємо стару клавіатуру ---
        await clean_previous_keyboard(state, bot, message.chat.id)
        # --- КІНЕЦЬ ОНОВЛЕНОЇ ЛОГІКИ ---

        products = await orm_find_products(search_query)
        if not products:
            sent_message = await message.answer(LEXICON.SEARCH_NO_RESULTS, reply_markup=None)
            # Зберігаємо ID, щоб потім його можна було прибрати
            await state.update_data(main_message_id=sent_message.message_id)
            return
            
        if len(products) == 1:
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
                # Редагуємо повідомлення зі списком результатів, перетворюючи його на картку
                sent_message = await send_or_edit_product_card(
                    bot=bot, 
                    chat_id=callback.message.chat.id, 
                    user_id=callback.from_user.id, 
                    product=product,
                    message_id=callback.message.message_id, # Редагуємо існуюче
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


@router.callback_query(F.data.startswith("card_qty:"))
async def handle_card_qty_change(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Обробка кнопок +/- на картці товару"""
    # Format: card_qty:action:product_id:current_qty:max_qty:price
    try:
        parts = callback.data.split(":")
        action = parts[1]
        product_id = int(parts[2])
        current_qty = int(parts[3])
        max_qty = int(parts[4])
        # Ціна може бути float
        price = float(parts[5])
        
        new_qty = current_qty
        if action == "inc":
            if current_qty < max_qty:
                new_qty += 1
            else:
                await callback.answer(f"Максимальна доступна кількість: {max_qty}", show_alert=True)
                return
        elif action == "dec":
            if current_qty > 1:
                new_qty -= 1
            else:
                await callback.answer("Мінімальна кількість: 1", show_alert=False)
                return
        
        if new_qty != current_qty:
             # Отримуємо пошуковий запит з state, щоб кнопка "Назад" працювала коректно
            data = await state.get_data()
            last_query = data.get('last_query')
            
            new_kb = get_product_card_kb(
                product_id=product_id,
                current_qty=new_qty,
                price=price,
                max_qty=max_qty,
                search_query=last_query
            )
            
            try:
                await callback.message.edit_reply_markup(reply_markup=new_kb)
            except TelegramBadRequest:
                pass # Message not modified
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling card qty change: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)


@router.callback_query(F.data.startswith("card_add:"))
async def handle_card_add_to_cart(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Обробка додавання товару в кошик"""
    # Format: card_add:product_id:quantity
    try:
        parts = callback.data.split(":")
        product_id = int(parts[1])
        quantity = int(parts[2])
        
        await orm_add_item_to_temp_list(callback.from_user.id, product_id, quantity)
        
        await callback.answer(f"✅ Додано {quantity} шт. у кошик", show_alert=False)
        
        # Оновлюємо картку, щоб показати актуальні залишки
        async with async_session() as session:
            product = await orm_get_product_by_id(session, product_id)
            if product:
                data = await state.get_data()
                last_query = data.get('last_query')
                
                await send_or_edit_product_card(
                    bot=bot,
                    chat_id=callback.message.chat.id,
                    user_id=callback.from_user.id,
                    product=product,
                    message_id=callback.message.message_id,
                    search_query=last_query
                )
                
    except Exception as e:
        logger.error(f"Error handling card add: {e}", exc_info=True)
        await callback.answer(LEXICON.UNEXPECTED_ERROR, show_alert=True)
