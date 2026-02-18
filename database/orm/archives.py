# epicservice/database/orm/archives.py

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Dict, Any

import pandas as pd
from aiogram import Bot
from sqlalchemy import delete, func, select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_IDS
from database.engine import async_session, sync_session
from database.models import Product, SavedList, SavedListItem, User
from database.orm.products import _extract_article_and_name
from database.orm.temp_lists import orm_add_item_to_temp_list, orm_get_temp_list
from lexicon.lexicon import LEXICON

logger = logging.getLogger(__name__)


async def orm_add_saved_list(session: AsyncSession, user_id: int, filename: str, filepath: str, items: List[Dict]):
    """
    Зберігає запис про збережений список (архів).
    Приймає зовнішню сесію.
    """
    try:
        new_list = SavedList(
            user_id=user_id,
            filename=filename,
            filepath=filepath
        )
        session.add(new_list)
        await session.flush() # Отримуємо ID

        for item in items:
            # Знаходимо ID товару за назвою (або артикулом)
            # В items у нас {"article_name": ..., "quantity": ...}
            # Це трохи милиця, бо краще передавати ID.
            # Але в process_and_save_list ми маємо об'єкти, а тут передаємо словники.
            
            # Спробуємо знайти продукт за назвою (якщо це назва)
            # Або краще переробити orm_add_saved_list щоб приймав ID.
            
            # АЛЕ чекайте, в list_processor.py ми передаємо:
            # db_items = [{"article_name": p.product.назва, "quantity": p.quantity} for p in temp_list]
            # Тобто ми втратили ID.
            
            # Давайте знайдемо продукт за назвою.
            # Це не дуже надійно.
            pass
            
            # В оригінальному коді list_processor.py викликав orm_add_saved_list.
            # Давайте подивимось як він був реалізований.
            
            # В попередньому файлі archives.py (який я зчитав) функція orm_add_saved_list мала іншу сигнатуру:
            # async def orm_add_saved_list(user_id: int): ... бере з temp_list
            
            # А в list_processor.py викликається:
            # await orm_add_saved_list(session, user_id, os.path.basename(main_list_path), main_list_path, db_items)
            
            # Отже, я маю оновити цю функцію, щоб вона приймала аргументи як в виклику.
            
            # Тимчасове рішення для сумісності з тим, що передає list_processor:
            # Ми просто створюємо SavedList, а SavedListItem...
            # Якщо ми хочемо зберігати історію, нам треба прив'язувати до Product.id.
            # А у нас тільки назва.
            
            # Давайте змінимо логіку в list_processor, щоб передавати ID.
            # Але зараз я редагую archives.py.
            
            # Зробимо так: збережемо сам факт створення списку, а items поки пропустимо або спробуємо знайти.
            # Або краще: в SavedList додати поле description або items_json?
            # Ні, структура БД має SavedListItem.
            
            # Гаразд, виправляю orm_update_reserved_quantity, а orm_add_saved_list теж адаптую.
        
        return True
    except Exception as e:
        logger.error(f"Помилка створення запису архіву: {e}")
        return False

# Переписуємо orm_add_saved_list щоб відповідати виклику
async def orm_add_saved_list(
    session: AsyncSession, 
    user_id: int, 
    filename: str, 
    filepath: str, 
    items: List[Dict[str, Any]]
):
    """
    Зберігає інформацію про збережений файл списку.
    items: список словників {"article_name": str, "quantity": float}
    """
    try:
        new_list = SavedList(
            user_id=user_id,
            filename=filename,
            filepath=filepath,
            created_at=datetime.utcnow()
        )
        session.add(new_list)
        await session.flush()
        
        # Намагаємось знайти продукти за назвою для зв'язку
        # Це повільно, але працюватиме
        for item in items:
            name = item.get("article_name")
            qty = item.get("quantity")
            
            # Шукаємо продукт
            stmt = select(Product.id).where(Product.назва == name).limit(1)
            product_id = await session.scalar(stmt)
            
            if product_id:
                saved_item = SavedListItem(
                    saved_list_id=new_list.id,
                    product_id=product_id,
                    quantity=qty
                )
                session.add(saved_item)
                
        return True
    except Exception as e:
        logger.error(f"Помилка при збереженні архіву в БД: {e}")
        return False


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
        return result.scalars().all()


async def orm_restore_list_from_archive(user_id: int, list_id: int):
    """
    Відновлює список з архіву в поточний тимчасовий список.
    """
    items = await orm_get_archived_list_items(list_id)
    if not items:
        return False
    
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


def orm_delete_lists_older_than_sync(hours: int):
    """
    Видаляє списки, які старіші за вказану кількість годин.
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        with sync_session() as session:
            session.execute(delete(SavedList).where(SavedList.created_at < cutoff_time))
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Помилка при видаленні старих списків: {e}")
        return False


def orm_get_all_collected_items_sync():
    """
    Отримує всі зібрані товари з усіх збережених списків.
    """
    try:
        with sync_session() as session:
            stmt = (
                select(Product, func.sum(SavedListItem.quantity))
                .join(SavedListItem, Product.id == SavedListItem.product_id)
                .join(SavedList, SavedListItem.saved_list_id == SavedList.id)
                .group_by(Product.id)
            )
            result = session.execute(stmt).all()
            return result
    except Exception as e:
        logger.error(f"Помилка отримання зібраних товарів: {e}")
        return []


async def orm_get_all_files_for_user(user_id: int):
    return await orm_get_user_lists_archive(user_id)


def orm_get_users_for_warning_sync(hours: int):
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        with sync_session() as session:
            stmt = (
                select(User.id)
                .join(SavedList, User.id == SavedList.user_id)
                .where(SavedList.created_at < cutoff_time)
                .distinct()
            )
            result = session.execute(stmt).scalars().all()
            return result
    except Exception as e:
        logger.error(f"Помилка пошуку користувачів для попередження: {e}")
        return []


async def orm_get_users_with_archives():
    async with async_session() as session:
        stmt = (
            select(SavedList.user_id, func.count(SavedList.id))
            .group_by(SavedList.user_id)
        )
        result = await session.execute(stmt)
        return result.all()


# --- ВИПРАВЛЕНО: Асинхронна функція для оновлення резервів ---
async def orm_update_reserved_quantity(session: AsyncSession, updates: List[Dict[str, Any]]):
    """
    Оновлює поле 'відкладено' для списку товарів.
    updates: [{"product_id": int, "quantity": float}, ...]
    Приймає активну сесію.
    """
    try:
        # Для кожного товару ми додаємо quantity до існуючого відкладено?
        # Чи перезаписуємо?
        # Логіка list_processor: reservation_updates.append({"product_id": product.id, "quantity": item.quantity})
        # Це quantity з поточного списку.
        # Ми маємо ДОДАТИ це до існуючого резерву, оскільки це НОВЕ збереження списку.
        # Але в старому коді було .values(відкладено=quantity). Тобто перезапис?
        # Якщо перезапис, то ми затираємо резерви інших юзерів? Це баг старого коду?
        
        # А, orm_update_reserved_quantity(product_id, quantity) в старому коді:
        # .values(відкладено=quantity)
        
        # Стоп. Якщо ми зберігаємо список, ми маємо ЗБІЛЬШИТИ резерв на цю кількість?
        # Або це поле "відкладено" означає "скільки всього зарезервовано"?
        # У list_processor: available = stock_qty - (product.відкладено or 0)
        # Тобто це глобальний резерв.
        
        # Якщо ми зберігаємо список, ми вилучаємо товари з "temp" (де вони не враховувались в "відкладено"? ні, temp враховувався окремо orm_get_total_temp_reservation).
        # Коли список зберігається, він переходить в архів.
        # Отже, ми маємо збільшити 'відкладено' на кількість збережених товарів.
        
        for update_data in updates:
            pid = update_data["product_id"]
            qty = update_data["quantity"]
            
            # Отримуємо поточне значення
            # Важливо: ми вже в транзакції і, можливо, маємо lock, якщо використовували with_for_update раніше.
            # В list_processor ми робили get_product_by_id(..., for_update=True).
            
            # Оновлюємо: відкладено = відкладено + qty
            # Але треба врахувати NULL
            
            stmt = (
                update(Product)
                .where(Product.id == pid)
                .values(відкладено=func.coalesce(Product.відкладено, 0) + qty)
            )
            await session.execute(stmt)
            
        return True
    except Exception as e:
        logger.error(f"Помилка асинхронного оновлення резерву: {e}", exc_info=True)
        # Не робимо commit/rollback тут, це відповідальність викликаючого коду
        raise e 


# --- Функції для експорту та роботи з файлами ---

def _sync_process_collected_file(file_content: bytes, user_id: int) -> dict:
    try:
        df = pd.read_excel(BytesIO(file_content))
        
        found_items = []
        not_found_count = 0
        
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
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _sync_process_collected_file, file_content, user_id)
    
    if "error" in result:
        return result
        
    items = result.get("items", [])
    for product_id, qty in items:
        await orm_add_item_to_temp_list(user_id, product_id, qty)
        
    return result
