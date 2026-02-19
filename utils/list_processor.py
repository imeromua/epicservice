# epicservice/utils/list_processor.py

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm import (orm_clear_temp_list, orm_get_product_by_id,
                          orm_get_temp_list, orm_update_reserved_quantity)
from utils.archive_manager import ACTIVE_DIR, rotate_user_files

logger = logging.getLogger(__name__)


async def _save_list_to_excel(
    items: List[Dict[str, Any]],
    user_id: int,
    department_id: Optional[int],
    total_sum: float,
    prefix: str = ""
) -> Optional[str]:
    """
    Зберігає список товарів у файл Excel з новим форматом назви.
    Формат: {prefix}{department}_{user_id}_{dd-mm-yyyy}_{hh-mm}.xlsx
    Зберігає в archives/active/
    Колонки: Артикул, Кількість, Ціна, Сума
    """
    if not items:
        return None
    try:
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
        
        department = department_id if department_id is not None else "list"
        file_name = f"{prefix}{department}_{user_id}_{timestamp}.xlsx"
        
        file_path = os.path.join(ACTIVE_DIR, file_name)

        df = pd.DataFrame(items)
        
        # Підсумки з порожніми клітинками для вирівнювання
        summary_df = pd.DataFrame([
            {"Артикул": "", "Кількість": "", "Ціна": "", "Сума": ""},
            {"Артикул": "К-ть артикулів:", "Кількість": len(df), "Ціна": "", "Сума": ""},
            {"Артикул": "Зібрано на суму:", "Кількість": "", "Ціна": "", "Сума": f"{total_sum:.2f} грн"}
        ])
        
        df_final = pd.concat([df, summary_df], ignore_index=True)

        df_final.to_excel(file_path, index=False, header=['Артикул', 'Кількість', 'Ціна', 'Сума'])
        
        logger.info(f"Файл успішно збережено: {file_path} з {len(df)} товарами на суму {total_sum:.2f} грн")
        return file_path
    except Exception as e:
        logger.error(f"Помилка збереження Excel файлу для користувача {user_id}: {e}", exc_info=True)
        return None


async def process_and_save_list(
    session: AsyncSession,
    user_id: int
) -> Tuple[Optional[str], Optional[str]]:
    """
    Централізована функція для обробки та збереження тимчасового списку.
    Всі операції з БД відбуваються в переданій сесії.
    Після збереження викликає rotate_user_files для автоочищення.
    """
    temp_list = await orm_get_temp_list(user_id, session=session)
    if not temp_list:
        return None, None

    department_id = temp_list[0].product.відділ

    in_stock_items, surplus_items = [], []
    reservation_updates = []
    
    total_in_stock_sum = 0.0
    total_surplus_sum = 0.0

    for item in temp_list:
        product = await orm_get_product_by_id(session, item.product_id, for_update=True)
        if not product:
            continue

        try:
            stock_qty = float(str(product.кількість).replace(',', '.'))
        except (ValueError, TypeError):
            stock_qty = 0

        available = stock_qty - (product.відкладено or 0)
        reservation_updates.append({"product_id": product.id, "quantity": item.quantity})
        
        price = float(product.ціна or 0.0)

        if item.quantity <= available:
            item_sum = item.quantity * price
            in_stock_items.append({
                "Артикул": product.артикул,
                "Кількість": item.quantity,
                "Ціна": price,
                "Сума": item_sum
            })
            total_in_stock_sum += item_sum
        else:
            if available > 0:
                available_sum = available * price
                in_stock_items.append({
                    "Артикул": product.артикул,
                    "Кількість": available,
                    "Ціна": price,
                    "Сума": available_sum
                })
                total_in_stock_sum += available_sum
            
            surplus_quantity = item.quantity - available
            surplus_sum = surplus_quantity * price
            surplus_items.append({
                "Артикул": product.артикул,
                "Кількість": surplus_quantity,
                "Ціна": price,
                "Сума": surplus_sum
            })
            total_surplus_sum += surplus_sum


    if reservation_updates:
        await orm_update_reserved_quantity(session, reservation_updates)

    main_list_path = await _save_list_to_excel(in_stock_items, user_id, department_id, total_in_stock_sum)
    surplus_list_path = await _save_list_to_excel(surplus_items, user_id, department_id, total_surplus_sum, "лишки_")

    # Ротація файлів юзера (залишаємо 10 новіших, решту в trash)
    rotate_user_files(user_id, limit=10)

    await orm_clear_temp_list(user_id, session=session)

    return main_list_path, surplus_list_path
