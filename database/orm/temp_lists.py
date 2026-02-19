# epicservice/database/orm/temp_lists.py

import logging
from typing import List, Tuple, Optional

from sqlalchemy import delete, func, select, distinct, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.engine import async_session, sync_session
from database.models import Product, TempList, SavedList

# Налаштовуємо логер для цього модуля
logger = logging.getLogger(__name__)


# --- Асинхронні функції для роботи з тимчасовими списками ---\n

async def orm_clear_temp_list(user_id: int, session: Optional[AsyncSession] = None):
    """
    Повністю очищує тимчасовий список для конкретного користувача.
    Підтримує зовнішню сесію для транзакцій.
    """
    if session:
        query = delete(TempList).where(TempList.user_id == user_id)
        await session.execute(query)
        # Не робимо commit, якщо сесія зовнішня
    else:
        async with async_session() as session:
            query = delete(TempList).where(TempList.user_id == user_id)
            await session.execute(query)
            await session.commit()


async def orm_add_item_to_temp_list(user_id: int, product_id: int, quantity: int):
    """
    Додає товар до тимчасового списку користувача.
    Перевіряє правило: один список = один відділ.
    """
    async with async_session() as session:
        # Отримуємо відділ нового товару
        product_query = select(Product).where(Product.id == product_id)
        new_product = await session.scalar(product_query)
        
        if not new_product:
            raise ValueError(f"Product {product_id} not found")
        
        new_department = new_product.відділ
        
        # Перевіряємо відділ поточного списку
        current_dept_query = (
            select(TempList)
            .where(TempList.user_id == user_id)
            .options(selectinload(TempList.product))
            .limit(1)
        )
        first_item = await session.scalar(current_dept_query)
        
        if first_item and first_item.product:
            current_department = first_item.product.відділ
            
            # Якщо відділи не співпадають - забороняємо
            if current_department != new_department:
                raise ValueError(
                    f"Неможливо додати товар з відділу {new_department}. "
                    f"Поточний список для відділу {current_department}. "
                    f"Збережіть або очистіть список."
                )
        
        # Перевіряємо чи товар вже є в списку
        query = select(TempList).where(
            TempList.user_id == user_id, TempList.product_id == product_id
        )
        existing_item = await session.scalar(query)

        if existing_item:
            existing_item.quantity += quantity
        else:
            new_item = TempList(
                user_id=user_id, product_id=product_id, quantity=quantity
            )
            session.add(new_item)

        await session.commit()


# --- Нові функції для редагування ---

async def orm_update_temp_list_item_quantity(user_id: int, product_id: int, new_quantity: int):
    """
    Оновлює кількість конкретного товару в тимчасовому списку.
    """
    async with async_session() as session:
        stmt = (
            update(TempList)
            .where(TempList.user_id == user_id, TempList.product_id == product_id)
            .values(quantity=new_quantity)
        )
        await session.execute(stmt)
        await session.commit()


async def orm_delete_temp_list_item(user_id: int, product_id: int):
    """
    Видаляє конкретний товар з тимчасового списку.
    """
    async with async_session() as session:
        stmt = delete(TempList).where(
            TempList.user_id == user_id, TempList.product_id == product_id
        )
        await session.execute(stmt)
        await session.commit()


# --- Решта функцій ---

async def orm_get_temp_list(user_id: int, session: Optional[AsyncSession] = None) -> list[TempList]:
    """
    Отримує поточний тимчасовий список користувача з усіма даними про товари.
    Підтримує зовнішню сесію.
    """
    query = (
        select(TempList)
        .where(TempList.user_id == user_id)
        .options(selectinload(TempList.product))
    )
    
    if session:
        result = await session.execute(query)
        return result.scalars().all()
    else:
        async with async_session() as session:
            result = await session.execute(query)
            return result.scalars().all()


async def orm_get_temp_list_department(user_id: int) -> int | None:
    """
    Визначає відділ поточного тимчасового списку користувача.
    """
    async with async_session() as session:
        query = (
            select(TempList)
            .where(TempList.user_id == user_id)
            .options(selectinload(TempList.product))
            .limit(1)
        )
        first_item = await session.scalar(query)
        return first_item.product.відділ if first_item and first_item.product else None


async def orm_get_temp_list_item_quantity(user_id: int, product_id: int) -> int:
    """
    Отримує кількість конкретного товару в тимчасовому списку поточного користувача.
    """
    async with async_session() as session:
        query = (
            select(func.sum(TempList.quantity))
            .where(TempList.user_id == user_id, TempList.product_id == product_id)
        )
        quantity = await session.scalar(query)
        return quantity or 0


async def orm_get_total_temp_reservation_for_product(product_id: int) -> int:
    """
    Отримує сумарну кількість товару у всіх тимчасових списках ВСІХ користувачів.
    """
    async with async_session() as session:
        query = (
            select(func.sum(TempList.quantity))
            .where(TempList.product_id == product_id)
        )
        total_quantity = await session.scalar(query)
        return total_quantity or 0


async def orm_get_users_with_active_lists() -> List[Tuple[int, int]]:
    """
    Знаходить користувачів, які мають активні (незбережені) списки.
    """
    async with async_session() as session:
        query = (
            select(TempList.user_id, func.count(TempList.id).label("item_count"))
            .group_by(TempList.user_id)
            .having(func.count(TempList.id) > 0)
        )
        result = await session.execute(query)
        return result.all()


def orm_get_all_temp_list_items_sync() -> list[TempList]:
    """
    Синхронно отримує всі позиції з усіх тимчасових списків з eager loading.
    """
    with sync_session() as session:
        query = select(TempList).options(selectinload(TempList.product))
        result = session.execute(query)
        return result.scalars().all()
