# epicservice/database/orm/archives.py

import logging
from collections import defaultdict
from datetime import datetime
from io import BytesIO

import pandas as pd
from aiogram import Bot
from sqlalchemy import delete, func, select

from config import ADMIN_IDS
from database.engine import async_session, sync_session
from database.models import Product, SavedList, SavedListItem
from database.orm.products import _extract_article_and_name
from database.orm.temp_lists import orm_add_item_to_temp_list, orm_get_temp_list
from lexicon.lexicon import LEXICON

logger = logging.getLogger(__name__)


async def orm_add_saved_list(user_id: int):
    """
    Зберігає поточний тимчасовий список у базу даних (архів).
    """
    async with async_session() as session:
        temp_items = await orm_get_temp_list(user_id)
        if not temp_items:
            return False

        # Створюємо новий запис про список
        new_list = SavedList(user_id=user_id)
        session.add(new_list)
        await session.flush()  # Щоб отримати ID нового списку

        # Переносимо товари з тимчасового списку в збережений
        for item in temp_items:
            saved_item = SavedListItem(
                saved_list_id=new_list.id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            session.add(saved_item)
        
        await session.commit()
        return True


async def orm_get_user_lists_archive(user_id: int):
    """
    Отримує збережені списки користувача.
    """
    async with async_session() as session:
        result = await session.execute(
            select(SavedList).where(SavedList.user_id == user_id).order_by(SavedList.created_at.desc())
        )
        return result.scalars().all()


async def orm_get_archived_list_items(list_id: int):
    """
    Отримує товари конкретного збереженого списку.
    """
    async with async_session() as session:
        result = await session.execute(
            select(SavedListItem).where(SavedListItem.saved_list_id == list_id)
        )
        items = result.scalars().all()
        # Жадібне завантаження product (або просто доступ до атрибутів, якщо lazy='selectin')
        return items


async def orm_restore_list_from_archive(user_id: int, list_id: int):
    """
    Відновлює список з архіву в поточний тимчасовий список.
    """
    items = await orm_get_archived_list_items(list_id)
    if not items:
        return False
    
    # Очищаємо поточний список (або додаємо до нього? Зазвичай відновлення замінює або додає)
    # Тут логіка додавання, судячи з виклику orm_add_item_to_temp_list
    for item in items:
        await orm_add_item_to_temp_list(user_id, item.product_id, item.quantity)
    return True


async def orm_delete_archived_list(list_id: int):
    """
    Видаляє збережений список.
    """
    async with async_session() as session:
        await session.execute(delete(SavedList).where(SavedList.id == list_id))
        await session.commit()


def orm_delete_all_saved_lists_sync():
    """
    Видаляє ВСІ збережені списки всіх користувачів (синхронно, для адмінки).
    """
    try:
        with sync_session() as session:
            session.execute(delete(SavedList))
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Помилка при видаленні всіх списків: {e}")
        return False


# --- Функції для експорту та роботи з файлами ---

def _sync_process_collected_file(file_content: bytes, user_id: int) -> dict:
    """
    Синхронно обробляє файл з зібраними залишками (імпорт зі сканера/файлу).
    """
    try:
        df = pd.read_excel(BytesIO(file_content))
        # Спрощена логіка: шукаємо колонку з артикулом/назвою та кількістю
        # Тут ми можемо використати SmartColumnMapper, але він в products.py
        # Для простоти поки залишимо базову логіку або скопіюємо частину
        
        # Але оскільки ми тут використовуємо _extract_article_and_name, то:
        found_items = []
        not_found_count = 0
        
        # Спробуємо знайти колонки
        headers = {str(col).lower(): col for col in df.columns}
        
        col_name = None
        for candidate in ["назва", "name", "товар", "product"]:
            if candidate in headers:
                col_name = headers[candidate]
                break
                
        col_qty = None
        for candidate in ["кількість", "qty", "quantity", "к-ть"]:
            if candidate in headers:
                col_qty = headers[candidate]
                break
        
        if not col_name or not col_qty:
            return {"error": "Не знайдено колонки 'Назва' або 'Кількість'"}

        with sync_session() as session:
            for _, row in df.iterrows():
                val = row[col_name]
                qty = row[col_qty]
                
                # --- ВИПРАВЛЕННЯ: Використовуємо нову функцію ---
                article, _ = _extract_article_and_name(val)
                
                if article:
                    product = session.execute(select(Product).where(Product.артикул == article)).scalar_one_or_none()
                    if product:
                        found_items.append((product.id, qty))
                    else:
                        not_found_count += 1
        
        return {"items": found_items, "not_found": not_found_count}

    except Exception as e:
        logger.error(f"Помилка обробки файлу зібраних товарів: {e}")
        return {"error": str(e)}


async def orm_import_collected_list(file_content: bytes, user_id: int):
    """
    Імпортує список зібраних товарів у тимчасовий список користувача.
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _sync_process_collected_file, file_content, user_id)
    
    if "error" in result:
        return result
        
    items = result.get("items", [])
    for product_id, qty in items:
        await orm_add_item_to_temp_list(user_id, product_id, qty)
        
    return result
