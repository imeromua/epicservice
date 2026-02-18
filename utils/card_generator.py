# epicservice/utils/card_generator.py

import logging
from typing import Union

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from database.models import Product
from database.orm import (orm_get_temp_list_item_quantity,
                          orm_get_total_temp_reservation_for_product)
from keyboards.inline import get_product_card_kb
from lexicon.lexicon import LEXICON
from utils.markdown_corrector import escape_markdown

logger = logging.getLogger(__name__)


def format_quantity(quantity_str: str) -> Union[int, float, str]:
    """
    Форматує рядок з кількістю у число (int або float).
    Повертає int, якщо число ціле, інакше float.
    Якщо конвертація неможлива, повертає оригінальний рядок.
    """
    try:
        quantity_float = float(str(quantity_str).replace(',', '.'))
        return int(quantity_float) if quantity_float.is_integer() else quantity_float
    except (ValueError, TypeError):
        return quantity_str


async def send_or_edit_product_card(
    bot: Bot,
    chat_id: int,
    user_id: int,
    product: Product,
    message_id: int = None,
    search_query: str | None = None,
    current_selection: int = 1 # Додано параметр для збереження вибору при оновленні (якщо треба)
) -> Message | None:
    """
    Формує та надсилає (або редагує) картку товару.
    """
    try:
        in_user_temp_list_qty = await orm_get_temp_list_item_quantity(user_id, product.id)
        total_temp_reserved = await orm_get_total_temp_reservation_for_product(product.id)

        try:
            stock_quantity = float(str(product.кількість).replace(',', '.'))
            permanently_reserved = product.відкладено or 0
            
            # available_for_anyone_qty - це скільки доступно ВЗАГАЛІ
            # (скільки можна ще додати до кошика)
            available_for_anyone_qty = stock_quantity - permanently_reserved - total_temp_reserved
            
            display_available_qty = format_quantity(available_for_anyone_qty)
            display_user_reserved_qty = format_quantity(in_user_temp_list_qty)
            
            # Max доступно для додавання (Selector Mode)
            # Якщо available < 0 (переліміт), то 0
            max_addable_qty = max(0, int(available_for_anyone_qty))

            price = product.ціна or 0.0
            
            current_stock_sum = available_for_anyone_qty * price
            reserved_sum = in_user_temp_list_qty * price
            
            display_stock_sum = f"{current_stock_sum:.2f}" if product.сума_залишку is not None else "---"
            display_reserved_sum = f"{reserved_sum:.2f}"
            display_months = product.місяці_без_руху if product.місяці_без_руху is not None else "---"

        except (ValueError, TypeError):
            display_available_qty = product.кількість
            max_addable_qty = 0
            display_user_reserved_qty = in_user_temp_list_qty
            display_stock_sum = "---"
            display_reserved_sum = "---"
            display_months = "---"
            price = 0.0

        # Додано article в форматування
        card_text = LEXICON.PRODUCT_CARD_TEMPLATE.format(
            article=escape_markdown(product.артикул), 
            name=escape_markdown(product.назва),
            department=escape_markdown(product.відділ),
            group=escape_markdown(product.група),
            months_no_movement=escape_markdown(display_months),
            stock_sum=escape_markdown(display_stock_sum),
            available_qty=escape_markdown(display_available_qty),
            reserved_qty=escape_markdown(display_user_reserved_qty),
            reserved_sum=escape_markdown(display_reserved_sum),
        )
        
        # Перевіряємо, щоб selection не перевищував доступне (якщо це можливо)
        # Але користувач може хотіти додати 1, навіть якщо доступно 0 (щоб потрапити в чергу? ні, у нас ліміт).
        # Коригуємо selection
        if max_addable_qty > 0:
             final_selection = min(current_selection, max_addable_qty)
             if final_selection == 0: final_selection = 1 # Щоб хоча б 1 показувало, якщо є доступне
        else:
             final_selection = 0 # Якщо нічого немає, то 0
             
        # Якщо доступно 0, то кнопка додавання буде неактивна або покаже 0?
        # Краще 0.

        keyboard = get_product_card_kb(
            product_id=product.id,
            current_qty=final_selection, # Це selected amount
            price=price,
            max_qty=max_addable_qty, # Це скільки ВІЛЬНО
            search_query=search_query
        )

        sent_message = None
        if message_id:
            try:
                sent_message = await bot.edit_message_text(
                    text=card_text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=keyboard
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
        else:
            sent_message = await bot.send_message(chat_id, card_text, reply_markup=keyboard)
        
        return sent_message

    except Exception as e:
        logger.error("Помилка відправки/редагування картки товару %s для %s: %s", product.id, user_id, e, exc_info=True)
        await bot.send_message(chat_id, LEXICON.UNEXPECTED_ERROR)
        return None
