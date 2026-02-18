# epicservice/database/orm/archives.py

import asyncio
import logging
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import async_session, sync_session
from database.models import Product, SavedList, SavedListItem, User
from database.orm.products import _extract_article_and_name
from database.orm.temp_lists import orm_add_item_to_temp_list

logger = logging.getLogger(__name__)


async def orm_add_saved_list(
    session: AsyncSession,
    user_id: int,
    filename: str,
    filepath: str,
    items: List[Dict[str, Any]]
):
    """
    Зберігає інформацію про збережений файл списку в рамках переданої сесії.
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

        for item in items:
            name = item.get("article_name")
            qty = item.get("quantity")

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
        logger.error("Помилка при збереженні архіву в БД: %s", e, exc_info=True)
        return False


async def orm_get_user_lists_archive(user_id: int):
    """
    Отримує збережені списки користувача.
    """
    async with async_session() as session:
        result = await session.execute(
            select(SavedList)
            .where(SavedList.user_id == user_id)
            .order_by(SavedList.created_at.desc())
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
        logger.error("Помилка при видаленні всіх списків: %s", e, exc_info=True)
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
        logger.error("Помилка при видаленні старих списків: %s", e, exc_info=True)
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
        logger.error("Помилка отримання зібраних товарів: %s", e, exc_info=True)
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
        logger.error("Помилка пошуку користувачів для попередження: %s", e, exc_info=True)
        return []


async def orm_get_users_with_archives():
    async with async_session() as session:
        stmt = (
            select(SavedList.user_id, func.count(SavedList.id))
            .group_by(SavedList.user_id)
        )
        result = await session.execute(stmt)
        return result.all()


async def orm_update_reserved_quantity(session: AsyncSession, updates: List[Dict[str, Any]]):
    """
    Збільшує поле 'відкладено' для списку товарів на відповідну кількість.
    updates: [{"product_id": int, "quantity": float}, ...]
    Приймає активну сесію — commit/rollback на відповідальності викликаючого.
    """
    try:
        for update_data in updates:
            pid = update_data["product_id"]
            qty = update_data["quantity"]
            stmt = (
                update(Product)
                .where(Product.id == pid)
                .values(відкладено=func.coalesce(Product.відкладено, 0) + qty)
            )
            await session.execute(stmt)
        return True
    except Exception as e:
        logger.error("Помилка оновлення резерву: %s", e, exc_info=True)
        raise


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
                    product = session.execute(
                        select(Product).where(Product.артикул == article)
                    ).scalar_one_or_none()
                    if product:
                        found_items.append((product.id, qty))
                    else:
                        not_found_count += 1

        return {"items": found_items, "not_found": not_found_count}

    except Exception as e:
        logger.error("Помилка обробки файлу зібраних товарів: %s", e, exc_info=True)
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
