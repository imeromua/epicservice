"""
Адміністративний роутер для управління системою через веб-інтерфейс.
Містить ендпоїнти для імпорту/експорту даних, управління користувачами та звітів.
"""

import asyncio
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import openpyxl
import pandas as pd
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import ADMIN_IDS, ARCHIVES_PATH, BOT_TOKEN, WEBAPP_URL
from database.orm import (
    orm_get_all_collected_items_sync,
    orm_get_all_products_sync,
    orm_get_all_temp_list_items_sync,
    orm_get_all_users_sync,
    orm_get_users_with_active_lists,
    orm_smart_import,
    orm_subtract_collected,
    orm_get_user_by_id,
)
from database.orm.products import SmartColumnMapper
from database.engine import async_session
from database.models import Product, ProductPhoto
from lexicon.lexicon import LEXICON
from utils.force_save_helper import force_save_user_list_web

logger = logging.getLogger(__name__)
router = APIRouter()
bot = Bot(token=BOT_TOKEN)

# Базова директорія webapp/ для побудови повних шляхів до фото
_BASE_DIR = Path(__file__).resolve().parent.parent  # webapp/


# === Middleware ===

def verify_admin(user_id: int) -> int:
    """
    Перевіряє, чи є користувач адміністратором.
    Викидає HTTPException(403) якщо користувач не має прав адміністратора.
    """
    if user_id not in ADMIN_IDS:
        logger.warning(f"Unauthorized admin access attempt by user {user_id}")
        raise HTTPException(status_code=403, detail="Access denied. Admin rights required.")
    return user_id


async def verify_admin_or_moderator(user_id: int) -> int:
    """
    Перевіряє, чи є користувач адміністратором або модератором.
    Адміни перевіряються за ADMIN_IDS, модератори — за роллю в БД.
    Викидає HTTPException(403) якщо доступ заборонено.
    """
    if user_id in ADMIN_IDS:
        return user_id
    user = await orm_get_user_by_id(user_id)
    if user and user.role == "moderator":
        return user_id
    logger.warning(f"Unauthorized access attempt by user {user_id}")
    raise HTTPException(status_code=403, detail="Access denied. Admin or moderator rights required.")


# === Pydantic Models ===

class AdminActionRequest(BaseModel):
    user_id: int
    action: str  # 'notify' або 'force_save'


class BroadcastRequest(BaseModel):
    user_id: int
    message: str


class ForceSaveRequest(BaseModel):
    user_id: int


# === Допоміжні функції ===

def cleanup_file(file_path: str):
    """Видаляє файл після відправки."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Файл {file_path} успішно видалено")
    except Exception as e:
        logger.error(f"Помилка видалення файлу {file_path}: {e}")


def _validate_excel_columns(df: pd.DataFrame) -> tuple[bool, str]:
    """Використовує SmartColumnMapper для перевірки наявності необхідних колонок."""
    mapping = SmartColumnMapper.map_columns(df)
    has_identity = "article" in mapping or "name" in mapping
    has_quantity = "quantity" in mapping or "stock_sum" in mapping
    if not has_identity:
        return False, "Не знайдено колонку з Артикулом або Назвою товару."
    if not has_quantity:
        return False, "Не знайдено колонку з Кількістю або Сумою залишку."
    return True, ""


def _format_import_report(result: dict) -> dict:
    """Форматує результат імпорту для JSON відповіді."""
    if not result:
        return {"success": False, "message": "Помилка імпорту. Перевірте формат файлу."}
    
    return {
        "success": True,
        "added": result.get('added', 0),
        "updated": result.get('updated', 0),
        "deactivated": result.get('deactivated', 0),
        "reactivated": result.get('reactivated', 0),
        "total_in_db": result.get('total_in_db', 0),
        "department_stats": result.get('department_stats', {})
    }


def _create_stock_report_sync() -> Optional[str]:
    """
    Створює звіт про залишки на складі.
    Формат: Відділ | Група | Артикул | Назва | Залишок (кількість) | Сума залишку (грн)
    """
    try:
        products = orm_get_all_products_sync()
        temp_list_items = orm_get_all_temp_list_items_sync()

        temp_reservations = {}
        for item in temp_list_items:
            temp_reservations[item.product_id] = temp_reservations.get(item.product_id, 0) + item.quantity

        report_data = []
        for product in products:
            try:
                stock_qty = float(str(product.кількість).replace(',', '.'))
            except (ValueError, TypeError):
                stock_qty = 0

            reserved = (product.відкладено or 0) + temp_reservations.get(product.id, 0)
            available = stock_qty - reserved
            available_sum = available * (product.ціна or 0.0)

            report_data.append({
                "Відділ": product.відділ,
                "Група": product.група,
                "Артикул": product.артикул,
                "Назва": product.назва,
                "Залишок (кількість)": int(available) if available == int(available) else available,
                "Сума залишку (грн)": round(available_sum, 2)
            })

        df = pd.DataFrame(report_data)
        os.makedirs(ARCHIVES_PATH, exist_ok=True)
        report_path = os.path.join(ARCHIVES_PATH, f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
        df.to_excel(report_path, index=False)
        return report_path
    except Exception as e:
        logger.error("Помилка створення звіту про залишки: %s", e, exc_info=True)
        return None


async def broadcast_import_update(result: dict):
    """
    Розсилає повідомлення всім користувачам про оновлення бази товарів.
    Повідомлення надсилаються ТІЛЬКИ з кнопкою "Відкрити Mini App".
    """
    loop = asyncio.get_running_loop()
    try:
        user_ids = await loop.run_in_executor(None, orm_get_all_users_sync)
        if not user_ids:
            logger.info("Користувачі для розсилки не знайдені.")
            return

        all_products = await loop.run_in_executor(None, orm_get_all_products_sync)
        total_sum = sum(p.сума_залишку for p in all_products if p.сума_залишку)

        summary_part = LEXICON.USER_IMPORT_NOTIFICATION_SUMMARY.format(
            total_in_db=result.get('total_in_db', 0),
            total_sum=f"{total_sum:,.2f}".replace(",", " ")
        )
        details_part = LEXICON.USER_IMPORT_NOTIFICATION_DETAILS.format(
            added=result.get('added', 0),
            updated=result.get('updated', 0),
            deactivated=result.get('deactivated', 0)
        )
        departments_part = LEXICON.USER_IMPORT_NOTIFICATION_DEPARTMENTS_TITLE
        dep_stats = result.get('department_stats', {})
        departments_lines = [
            LEXICON.USER_IMPORT_NOTIFICATION_DEPARTMENT_ITEM.format(dep_id=dep_id, count=count)
            for dep_id, count in sorted(dep_stats.items())
        ]
        message_text = (
            LEXICON.USER_IMPORT_NOTIFICATION_TITLE + summary_part +
            details_part + departments_part + "".join(departments_lines)
        )

        # Клавіатура ТІЛЬКИ з кнопкою Mini App
        mini_app_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Відкрити EpicService", web_app=WebAppInfo(url=WEBAPP_URL))]
            ]
        )

        sent_count = 0
        for user_id in user_ids:
            try:
                await bot.send_message(
                    user_id, 
                    message_text, 
                    reply_markup=mini_app_kb,
                    parse_mode='HTML'
                )
                sent_count += 1
            except Exception as e:
                logger.warning("Не вдалося надіслати сповіщення користувачу %s: %s", user_id, e)

        logger.info("Розсилку завершено. Надіслано %d/%d повідомлень.", sent_count, len(user_ids))
    except Exception as e:
        logger.error("Критична помилка під час розсилки: %s", e, exc_info=True)


# === Ендпоїнти ===

@router.get("/users")
async def get_all_users(user_id: int = Query(...)):
    """
    Отримати список всіх користувачів системи.
    Потрібні права адміністратора.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        user_ids = await loop.run_in_executor(None, orm_get_all_users_sync)
        return JSONResponse(content={
            "success": True,
            "users": user_ids,
            "count": len(user_ids)
        })
    except Exception as e:
        logger.error("Помилка отримання користувачів: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання користувачів"}, status_code=500)


@router.get("/users/active")
async def get_active_users(user_id: int = Query(...)):
    """
    Отримати користувачів з активними списками (temp_list).
    Потрібні права адміністратора.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        active_users_raw = await orm_get_users_with_active_lists()
        temp_list_items = await loop.run_in_executor(None, orm_get_all_temp_list_items_sync)
        
        # Витягуємо username/first_name з БД
        async with async_session() as session:
            result = await session.execute(
                text("SELECT id, username, first_name FROM users")
            )
            users_info = {row[0]: {"username": row[1], "first_name": row[2]} for row in result.fetchall()}
        
        # Групуємо по користувачах
        user_data = {}
        for item in temp_list_items:
            if item.user_id not in user_data:
                user_info = users_info.get(item.user_id, {})
                # Формуємо комбо: Ім'я (@username)
                first_name = user_info.get('first_name', '')
                username = user_info.get('username', '')
                
                if first_name and username:
                    display_name = f"{first_name} (@{username})"
                elif first_name:
                    display_name = first_name
                elif username:
                    display_name = f"@{username}"
                else:
                    display_name = f"User {item.user_id}"
                
                user_data[item.user_id] = {
                    "user_id": item.user_id,
                    "username": display_name,
                    "department": None,
                    "items_count": 0,
                    "total_sum": 0.0
                }
            user_data[item.user_id]["items_count"] += 1
            user_data[item.user_id]["total_sum"] += (item.quantity * (item.product.ціна or 0.0))
            if not user_data[item.user_id]["department"]:
                user_data[item.user_id]["department"] = item.product.відділ
        
        return JSONResponse(content={
            "success": True,
            "users": list(user_data.values())
        })
    except Exception as e:
        logger.error("Помилка отримання активних користувачів: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання активних користувачів"}, status_code=500)


@router.get("/archives")
async def list_archives(user_id: int = Query(...)):
    """
    Отримати список всіх архівів користувачів.
    Читає файли з /home/anubis/epicservice/archives/active.
    """
    verify_admin(user_id)
    try:
        archives_dir = os.path.join(ARCHIVES_PATH, "active")
        
        if not os.path.exists(archives_dir):
            return JSONResponse(content={
                "success": True,
                "files": [],
                "message": "Папка архівів не існує"
            })
        
        files = []
        for filename in os.listdir(archives_dir):
            filepath = os.path.join(archives_dir, filename)
            if os.path.isfile(filepath) and filename.endswith('.xlsx'):
                stat = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # Сортуємо за датою модифікації (новіші першими)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "files": files,
            "count": len(files)
        })
    
    except Exception as e:
        logger.error("Помилка отримання списку архівів: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": "Помилка отримання списку архівів"},
            status_code=500
        )


@router.get("/archives/download/{filename}")
async def download_archive(filename: str, user_id: int = Query(...)):
    """
    Скачати конкретний файл архіву.
    """
    verify_admin(user_id)
    try:
        # Безпека: перевіряємо що filename не містить шляхи
        if '/' in filename or '\\' in filename or '..' in filename:
            raise HTTPException(status_code=400, detail="Недозволене ім'я файлу")
        
        filepath = os.path.join(ARCHIVES_PATH, "active", filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Файл не знайдено")
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Помилка завантаження архіву %s: %s", filename, e, exc_info=True)
        return JSONResponse(
            content={"error": "Помилка завантаження файлу"},
            status_code=500
        )


@router.get("/archives/download-all")
async def download_all_archives(user_id: int = Query(...), background_tasks: BackgroundTasks = None):
    """
    Скачати всі архіви одним ZIP файлом.
    """
    verify_admin(user_id)
    try:
        archives_dir = os.path.join(ARCHIVES_PATH, "active")
        
        if not os.path.exists(archives_dir):
            raise HTTPException(status_code=404, detail="Папка архівів не існує")
        
        # Створюємо тимчасовий ZIP файл
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_path = os.path.join(tempfile.gettempdir(), f"archives_{timestamp}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in os.listdir(archives_dir):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(archives_dir, filename)
                    zipf.write(filepath, arcname=filename)
        
        if background_tasks:
            background_tasks.add_task(cleanup_file, zip_path)
        
        return FileResponse(
            path=zip_path,
            filename=f"archives_{timestamp}.zip",
            media_type="application/zip"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Помилка створення ZIP архіву: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": "Помилка створення архіву"},
            status_code=500
        )


@router.post("/import")
async def import_products(
    file: UploadFile = File(...),
    user_id: int = Query(...),
    notify_users: bool = Query(False)
):
    """
    Імпорт товарів з Excel файлу.
    Підтримує розумне розпізнавання колонок.
    Опціонально розсилає сповіщення користувачам.
    """
    await verify_admin_or_moderator(user_id)
    
    if not file.filename.endswith((".xlsx", ".xls")):
        return JSONResponse(
            content={"error": "Невірний формат файлу. Потрібен Excel (.xlsx або .xls)"},
            status_code=400
        )

    tmp_fd, temp_file_path = tempfile.mkstemp(suffix=".xlsx", prefix=f"import_{user_id}_")
    os.close(tmp_fd)

    try:
        # Зберігаємо завантажений файл
        contents = await file.read()
        with open(temp_file_path, 'wb') as f:
            f.write(contents)

        # Читаємо та валідуємо
        df = await asyncio.to_thread(pd.read_excel, temp_file_path)
        is_valid, error_msg = _validate_excel_columns(df)
        
        if not is_valid:
            return JSONResponse(
                content={"error": f"Невірна структура файлу: {error_msg}"},
                status_code=400
            )

        # Виконуємо імпорт
        result = await orm_smart_import(df)
        if not result:
            return JSONResponse(
                content={"error": "Не вдалося розпізнати дані у файлі"},
                status_code=500
            )

        # Формуємо відповідь
        response_data = _format_import_report(result)

        # Опціонально розсилаємо сповіщення
        if notify_users:
            asyncio.create_task(broadcast_import_update(result))
            response_data["notification"] = "Розсилка запущена у фоновому режимі"

        return JSONResponse(content=response_data)

    except SQLAlchemyError as e:
        logger.critical("Помилка БД під час імпорту: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": f"Помилка бази даних: {str(e)}"},
            status_code=500
        )
    except Exception as e:
        logger.error("Критична помилка при імпорті: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": f"Помилка обробки файлу: {str(e)}"},
            status_code=500
        )
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/subtract-collected")
async def subtract_collected(
    file: UploadFile = File(...),
    user_id: int = Query(...)
):
    """
    Відняти зібране — коригування залишків з Excel-файлу (2 колонки: артикул + кількість).
    Перевіряє блокування перед змінами. Повертає детальний звіт.
    """
    await verify_admin_or_moderator(user_id)

    if not file.filename.endswith((".xlsx", ".xls")):
        return JSONResponse(
            content={"error": "Невірний формат файлу. Потрібен Excel (.xlsx або .xls)"},
            status_code=400
        )

    contents = await file.read()

    # --- Перевірки блокування ---
    active_list_users = await orm_get_users_with_active_lists()
    if active_list_users:
        return JSONResponse(
            content={"blocked": True, "reason": "active_list"},
            status_code=409
        )

    async with async_session() as session:
        result_reserved = await session.execute(
            text("SELECT COUNT(*) FROM products WHERE відкладено > 0")
        )
        reserved_count = result_reserved.scalar()
    if reserved_count and reserved_count > 0:
        return JSONResponse(
            content={"blocked": True, "reason": "reserved_exists"},
            status_code=409
        )

    # --- Парсинг файлу ---
    def _parse_xlsx(data: bytes):
        import io
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.worksheets[0]

        rows_total = 0
        rows_valid = 0
        article_map: dict = {}
        skipped_invalid = []

        for row_idx, row in enumerate(ws.iter_rows(min_row=1), start=1):
            cell_a = row[0].value if len(row) > 0 else None
            cell_b = row[1].value if len(row) > 1 else None

            if cell_a is None and cell_b is None:
                continue

            rows_total += 1

            article = str(cell_a).strip() if cell_a is not None else ""
            if not article:
                skipped_invalid.append({
                    "row": row_idx,
                    "article": article,
                    "qty": str(cell_b),
                    "reason": "empty_article"
                })
                continue

            try:
                qty = int(cell_b)
                if qty <= 0:
                    raise ValueError("qty <= 0")
            except (TypeError, ValueError):
                skipped_invalid.append({
                    "row": row_idx,
                    "article": article,
                    "qty": str(cell_b),
                    "reason": "invalid_qty"
                })
                continue

            rows_valid += 1
            article_map[article] = article_map.get(article, 0) + qty

        wb.close()
        return rows_total, rows_valid, article_map, skipped_invalid

    try:
        rows_total, rows_valid, article_map, skipped_invalid = await asyncio.to_thread(
            _parse_xlsx, contents
        )
    except Exception as e:
        logger.error("Помилка парсингу файлу subtract-collected: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": f"Помилка обробки файлу: {str(e)}"},
            status_code=500
        )

    # --- Застосування змін ---
    updated = 0
    skipped_not_found = 0
    skipped_inactive = 0
    set_to_zero_list = []

    try:
        async with async_session() as session:
            async with session.begin():
                from sqlalchemy import select as sa_select
                for article, qty in article_map.items():
                    row_result = await session.execute(
                        sa_select(Product).where(Product.артикул == article)
                    )
                    product = row_result.scalar_one_or_none()

                    if product is None:
                        skipped_not_found += 1
                        continue

                    if not product.активний:
                        skipped_inactive += 1
                        continue

                    try:
                        db_before = int(float(str(product.кількість).replace(",", ".")))
                    except (ValueError, TypeError):
                        db_before = 0

                    new_qty = db_before - qty
                    if new_qty < 0:
                        set_to_zero_list.append({
                            "article": article,
                            "db_before": db_before,
                            "subtract": qty,
                            "db_after": 0
                        })
                        product.кількість = "0"
                    else:
                        product.кількість = str(new_qty)
                        updated += 1

    except SQLAlchemyError as e:
        logger.critical("Помилка БД під час subtract-collected: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": f"Помилка бази даних: {str(e)}"},
            status_code=500
        )

    return JSONResponse(content={
        "success": True,
        "summary": {
            "rows_total": rows_total,
            "rows_valid": rows_valid,
            "unique_articles": len(article_map),
            "updated": updated,
            "set_to_zero": len(set_to_zero_list),
            "skipped_not_found": skipped_not_found,
            "skipped_inactive": skipped_inactive,
            "skipped_invalid": len(skipped_invalid),
        },
        "details": {
            "set_to_zero": set_to_zero_list,
            "skipped_invalid": skipped_invalid,
        }
    })


@router.get("/export/stock")
async def export_stock_report(user_id: int = Query(...), background_tasks: BackgroundTasks = None):
    """
    Експорт звіту про залишки на складі.
    Враховує резерви з temp_list.
    """
    await verify_admin_or_moderator(user_id)
    try:
        loop = asyncio.get_running_loop()
        report_path = await loop.run_in_executor(None, _create_stock_report_sync)

        if not report_path:
            return JSONResponse(
                content={"error": "Не вдалося створити звіт"},
                status_code=500
            )

        if background_tasks:
            background_tasks.add_task(cleanup_file, report_path)

        return FileResponse(
            path=report_path,
            filename=os.path.basename(report_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        logger.error("Помилка експорту залишків: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": "Помилка створення звіту"},
            status_code=500
        )


@router.get("/summary")
async def get_summary_stats(user_id: int = Query(...)):
    """
    Отримати зведену статистику по відділах у форматі JSON.
    Показує кількість артикулів та загальну суму збору.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        all_products = await loop.run_in_executor(None, orm_get_all_products_sync)

        if not all_products:
            return JSONResponse(content={
                "success": False,
                "message": "Немає даних для формування звіту"
            }, status_code=404)

        # Групуємо по відділах
        dept_stats = {}
        total_count = 0
        total_sum = 0.0
        
        for product in all_products:
            dept = product.відділ
            if dept not in dept_stats:
                dept_stats[dept] = {"count": 0, "total_sum": 0.0}
            dept_stats[dept]["count"] += 1
            dept_stats[dept]["total_sum"] += (product.сума_залишку or 0.0)
            total_count += 1
            total_sum += (product.сума_залишку or 0.0)

        # Форматуємо для відповіді
        departments = [
            {
                "department_id": dept_id,
                "count": stats["count"],
                "total_sum": round(stats["total_sum"], 2)
            }
            for dept_id, stats in sorted(dept_stats.items())
        ]

        return JSONResponse(content={
            "success": True,
            "total_count": total_count,
            "total_sum": round(total_sum, 2),
            "departments": departments
        })

    except Exception as e:
        logger.error("Помилка отримання зведеної статистики: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": "Помилка отримання статистики"},
            status_code=500
        )


@router.post("/force-save/{target_user_id}")
async def force_save_user_list_endpoint(
    target_user_id: int,
    request: ForceSaveRequest
):
    """
    Примусово зберегти список користувача.
    Використовується перед важливими операціями (імпорт, експорт).
    """
    verify_admin(request.user_id)
    
    try:
        # Використовуємо веб-версію без FSMContext
        success = await force_save_user_list_web(target_user_id, bot)
        
        if success:
            return JSONResponse(content={
                "success": True,
                "message": f"Список користувача {target_user_id} успішно збережено"
            })
        else:
            return JSONResponse(content={
                "success": False,
                "message": f"Не вдалося зберегти список користувача {target_user_id}"
            }, status_code=500)

    except Exception as e:
        logger.error("Помилка примусового збереження для користувача %s: %s", target_user_id, e, exc_info=True)
        return JSONResponse(
            content={"error": "Помилка збереження списку"},
            status_code=500
        )


@router.post("/broadcast")
async def broadcast_message(
    request: BroadcastRequest
):
    """
    Розіслати повідомлення всім користувачам системи.
    Використовується для важливих оголошень.
    """
    verify_admin(request.user_id)
    
    try:
        loop = asyncio.get_running_loop()
        user_ids = await loop.run_in_executor(None, orm_get_all_users_sync)
        
        if not user_ids:
            return JSONResponse(
                content={"message": "Немає користувачів для розсилки"},
                status_code=404
            )

        sent_count = 0
        failed_count = 0
        
        for uid in user_ids:
            try:
                await bot.send_message(uid, request.message)
                sent_count += 1
            except Exception as e:
                logger.warning("Не вдалося надіслати повідомлення користувачу %s: %s", uid, e)
                failed_count += 1

        return JSONResponse(content={
            "success": True,
            "message": "Розсилка завершена",
            "sent": sent_count,
            "failed": failed_count,
            "total": len(user_ids)
        })

    except Exception as e:
        logger.error("Помилка розсилки: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": "Помилка розсилки повідомлень"},
            status_code=500
        )


@router.get("/statistics")
async def get_system_statistics(user_id: int = Query(...)):
    """
    Отримати загальну статистику системи для адмін-панелі.
    Включає інформацію про користувачів, товари та резерви.
    """
    verify_admin(user_id)
    
    try:
        loop = asyncio.get_running_loop()
        
        # Збираємо статистику паралельно
        all_users = await loop.run_in_executor(None, orm_get_all_users_sync)
        all_products = await loop.run_in_executor(None, orm_get_all_products_sync)
        active_users_data = await orm_get_users_with_active_lists()
        temp_list_items = await loop.run_in_executor(None, orm_get_all_temp_list_items_sync)
        
        # Підраховуємо загальну зарезервовану суму
        total_reserved_sum = sum(item.quantity * (item.product.ціна or 0.0) for item in temp_list_items)
        
        return JSONResponse(content={
            "total_users": len(all_users),
            "active_users": len(active_users_data),
            "total_products": len(all_products),
            "total_reserved_sum": round(total_reserved_sum, 2)
        })

    except Exception as e:
        logger.error("Помилка отримання статистики: %s", e, exc_info=True)
        return JSONResponse(
            content={"error": "Помилка отримання статистики"},
            status_code=500
        )


@router.get("/users/all")
async def get_all_users_with_stats(user_id: int = Query(...)):
    """
    Отримати всіх користувачів з історією архівів та загальною сумою.
    Формат файлів: {відділ}_{user_id}_{дата}_{час}.xlsx
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        user_ids = await loop.run_in_executor(None, orm_get_all_users_sync)
        
        # Витягуємо username/first_name з БД
        async with async_session() as session:
            result = await session.execute(
                text("SELECT id, username, first_name FROM users")
            )
            users_info = {row[0]: {"username": row[1], "first_name": row[2]} for row in result.fetchall()}
        
        users_data = []
        archives_dir = os.path.join(ARCHIVES_PATH, "active")
        
        for uid in user_ids:
            # Підраховуємо архіви користувача
            archives_count = 0
            total_amount = 0.0
            last_activity = None
            
            if os.path.exists(archives_dir):
                # Шукаємо файли за патерном: *_{user_id}_*.xlsx
                user_files = [f for f in os.listdir(archives_dir) 
                             if f.endswith('.xlsx') and f"_{uid}_" in f]
                archives_count = len(user_files)
                
                # Знаходимо останній файл
                if user_files:
                    latest_file = max(user_files, key=lambda f: os.path.getmtime(os.path.join(archives_dir, f)))
                    last_activity = datetime.fromtimestamp(
                        os.path.getmtime(os.path.join(archives_dir, latest_file))
                    ).strftime('%d.%m.%Y %H:%M')
                    
                    # Читаємо всі файли користувача для підрахунку суми
                    for filename in user_files:
                        try:
                            filepath = os.path.join(archives_dir, filename)
                            df = pd.read_excel(filepath)
                            if 'Сума' in df.columns:
                                # Конвертуємо в числа, ігноруючи помилки, фільтруємо NaN
                                suma_column = pd.to_numeric(df['Сума'], errors='coerce').dropna()
                                total_amount += suma_column.sum()
                        except Exception as e:
                            logger.warning(f"Не вдалося прочитати {filename}: {e}")
            
            # Формуємо display name
            user_info = users_info.get(uid, {})
            # Формуємо комбо: Ім'я (@username)
            first_name = user_info.get('first_name', '')
            username = user_info.get('username', '')
            
            if first_name and username:
                display_name = f"{first_name} (@{username})"
            elif first_name:
                display_name = first_name
            elif username:
                display_name = f"@{username}"
            else:
                display_name = f"User {uid}"
            
            users_data.append({
                "user_id": uid,
                "username": display_name,
                "archives_count": archives_count,
                "total_amount": round(total_amount, 2),
                "last_activity": last_activity
            })
        
        # Сортуємо за кількістю архівів
        users_data.sort(key=lambda x: x['archives_count'], reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "users": users_data
        })
    
    except Exception as e:
        logger.error("Помилка отримання користувачів: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання користувачів"}, status_code=500)


@router.get("/products/info")
async def get_products_info(user_id: int = Query(...)):
    """
    Отримати інформацію про товари з було/стало статистикою.
    Враховує доступні товари та зібрані за сесію.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        all_products = await loop.run_in_executor(None, orm_get_all_products_sync)
        temp_list_items = await loop.run_in_executor(None, orm_get_all_temp_list_items_sync)
        
        if not all_products:
            return JSONResponse(content={
                "success": False,
                "message": "Немає товарів у базі"
            }, status_code=404)
        
        # Підраховуємо резерви з temp_list
        temp_reservations = {}
        for item in temp_list_items:
            temp_reservations[item.product_id] = temp_reservations.get(item.product_id, 0) + item.quantity
        
        # Розділяємо на доступні та зібрані
        available_products = []
        collected_products = []
        dept_stats_current = {}
        dept_stats_original = {}
        current_sum = 0.0
        collected_sum = 0.0
        
        for product in all_products:
            try:
                stock_qty = float(str(product.кількість).replace(',', '.'))
            except (ValueError, TypeError):
                stock_qty = 0
            
            # Рахуємо доступну кількість
            reserved = (product.відкладено or 0) + temp_reservations.get(product.id, 0)
            available = stock_qty - reserved
            dept = product.відділ
            price = product.ціна or 0.0
            
            if available > 0:
                # Доступні товари
                available_products.append(product)
                dept_stats_current[dept] = dept_stats_current.get(dept, 0) + 1
                current_sum += available * price
            elif reserved > 0 or stock_qty == 0:
                # Зібрані товари (було, але відкладено або кількість 0)
                collected_products.append(product)
                collected_sum += reserved * price
        
        # Було = доступні + зібрані
        for product in available_products + collected_products:
            dept = product.відділ
            dept_stats_original[dept] = dept_stats_original.get(dept, 0) + 1
        
        departments = [
            {
                "department": dept_id,
                "current_count": dept_stats_current.get(dept_id, 0),
                "original_count": dept_stats_original.get(dept_id, 0)
            }
            for dept_id in sorted(set(list(dept_stats_current.keys()) + list(dept_stats_original.keys())))
        ]
        
        # Остання дата імпорту
        last_import = None
        if all_products and hasattr(all_products[0], 'created_at'):
            last_import = all_products[0].created_at.strftime('%d.%m - %H:%M')
        
        original_count = len(available_products) + len(collected_products)
        original_sum = current_sum + collected_sum
        
        return JSONResponse(content={
            "success": True,
            # Поточний стан
            "current_articles": len(available_products),
            "current_sum": round(current_sum, 2),
            # Початковий стан
            "original_articles": original_count,
            "original_sum": round(original_sum, 2),
            # Зібрано
            "collected_articles": len(collected_products),
            "collected_sum": round(collected_sum, 2),
            # Деталі
            "departments": departments,
            "last_import": last_import
        })
    
    except Exception as e:
        logger.error("Помилка отримання інформації про товари: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання даних"}, status_code=500)


@router.get("/reserved/by-department")
async def get_reserved_by_department(user_id: int = Query(...)):
    """
    Отримати розбивку резервів по відділах з детальною статистикою.
    """
    verify_admin(user_id)
    try:
        loop = asyncio.get_running_loop()
        temp_list_items = await loop.run_in_executor(None, orm_get_all_temp_list_items_sync)
        
        if not temp_list_items:
            return JSONResponse(content={
                "success": True,
                "departments": []
            })
        
        # Групуємо по відділах
        dept_data = {}
        for item in temp_list_items:
            dept = item.product.відділ
            if dept not in dept_data:
                dept_data[dept] = {
                    "department": dept,
                    "reserved_sum": 0.0,
                    "products_count": set(),
                    "users_count": set()
                }
            
            dept_data[dept]["reserved_sum"] += item.quantity * (item.product.ціна or 0.0)
            dept_data[dept]["products_count"].add(item.product_id)
            dept_data[dept]["users_count"].add(item.user_id)
        
        # Конвертуємо set в count
        departments = []
        for dept_id, data in sorted(dept_data.items()):
            departments.append({
                "department": dept_id,
                "reserved_sum": round(data["reserved_sum"], 2),
                "products_count": len(data["products_count"]),
                "users_count": len(data["users_count"])
            })
        
        # Сортуємо за сумою резерву
        departments.sort(key=lambda x: x["reserved_sum"], reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "departments": departments
        })
    
    except Exception as e:
        logger.error("Помилка отримання резервів по відділах: %s", e, exc_info=True)
        return JSONResponse(content={"error": "Помилка отримання даних"}, status_code=500)


# ==================== DANGER ZONE ENDPOINTS ====================

@router.post("/danger/clear-database")
async def danger_clear_database(user_id: int = Query(...)):
    """
    🚨 КРИТИЧНА ОПЕРАЦІЯ 🚨
    Видаляє ВСІ товари з бази даних.
    Незворотна операція!
    """
    verify_admin(user_id)
    
    try:
        logger.critical("⚠️ DANGER ZONE: User %s initiated CLEAR DATABASE operation", user_id)
        
        # Видаляємо з CASCADE для підтаблиць
        async with async_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM products"))
            count = result.scalar()
            
            # Видаляємо product_photos спочатку (foreign key)
            await session.execute(text("DELETE FROM product_photos"))
            # Потім products
            await session.execute(text("DELETE FROM products"))
            await session.commit()
            
            logger.critical("✅ Database cleared: %d products deleted by admin %s", count, user_id)
            
            return JSONResponse(content={
                "success": True,
                "message": "База даних очищена",
                "deleted_count": count
            })
    
    except Exception as e:
        logger.error("Помилка очищення БД: %s", e, exc_info=True)
        return JSONResponse(
            content={"success": False, "message": f"Помилка: {str(e)}"},
            status_code=500
        )


@router.post("/danger/delete-all-photos")
async def danger_delete_all_photos(user_id: int = Query(...)):
    """
    🚨 КРИТИЧНА ОПЕРАЦІЯ 🚨
    Видаляє ВСІ фото з серверу (за file_path з БД) та записи з БД.
    file_path в БД: "uploads/photos/61605401/photo_0.jpg"
    Повний шлях: webapp/static/ + file_path
    Незворотна операція!
    """
    verify_admin(user_id)
    
    try:
        logger.critical("⚠️ DANGER ZONE: User %s initiated DELETE ALL PHOTOS operation", user_id)
        
        deleted_files = 0
        deleted_db_records = 0
        
        # Спочатку отримуємо всі file_path з БД
        async with async_session() as session:
            result = await session.execute(
                text("SELECT file_path FROM product_photos")
            )
            file_paths = [row[0] for row in result.fetchall()]
            
            logger.info(f"Found {len(file_paths)} photo records in database")
            
            # Видаляємо файли з сервера
            # file_path приклад: "uploads/photos/61605401/photo_0.jpg"
            # Повний шлях: /home/anubis/epicservice/webapp/static/uploads/photos/61605401/photo_0.jpg
            for relative_path in file_paths:
                try:
                    full_path = _BASE_DIR / "static" / relative_path
                    if full_path.exists():
                        full_path.unlink()
                        deleted_files += 1
                        logger.debug(f"Deleted file: {full_path}")
                    else:
                        logger.warning(f"File not found: {full_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {full_path}: {e}")
            
            # Видаляємо записи з БД
            delete_result = await session.execute(text("DELETE FROM product_photos"))
            deleted_db_records = delete_result.rowcount
            await session.commit()
        
        logger.critical(
            "✅ All photos deleted by admin %s: %d files, %d DB records",
            user_id, deleted_files, deleted_db_records
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "Всі фото видалено",
            "deleted_count": deleted_files,
            "deleted_db_records": deleted_db_records
        })
    
    except Exception as e:
        logger.error("Помилка видалення фото: %s", e, exc_info=True)
        return JSONResponse(
            content={"success": False, "message": f"Помилка: {str(e)}"},
            status_code=500
        )


@router.post("/danger/reset-moderation")
async def danger_reset_moderation(user_id: int = Query(...)):
    """
    ⚠️ Скидає статус модерації для ВСІХ фото.
    Всі фото стануть 'pending' (очікують модерації).
    """
    verify_admin(user_id)
    
    try:
        logger.warning("⚠️ DANGER ZONE: User %s initiated RESET MODERATION operation", user_id)
        
        async with async_session() as session:
            # Правильна назва колонки: status (не moderation_status!)
            result = await session.execute(
                text("UPDATE product_photos SET status = 'pending', moderated_at = NULL, moderated_by = NULL")
            )
            await session.commit()
            
            logger.info("✅ Moderation reset: %d photos by admin %s", result.rowcount, user_id)
            
            return JSONResponse(content={
                "success": True,
                "message": "Статус модерації скинуто",
                "reset_count": result.rowcount
            })
    
    except Exception as e:
        logger.error("Помилка скидання модерації: %s", e, exc_info=True)
        return JSONResponse(
            content={"success": False, "message": f"Помилка: {str(e)}"},
            status_code=500
        )


@router.post("/danger/delete-all-archives")
async def danger_delete_all_archives(user_id: int = Query(...)):
    """
    🚨 КРИТИЧНА ОПЕРАЦІЯ 🚨
    Видаляє ВСІ архіви користувачів.
    Незворотна операція!
    """
    verify_admin(user_id)
    
    try:
        logger.critical("⚠️ DANGER ZONE: User %s initiated DELETE ALL ARCHIVES operation", user_id)
        
        archives_dir = os.path.join(ARCHIVES_PATH, "active")
        deleted_files = 0
        
        if os.path.exists(archives_dir):
            for filename in os.listdir(archives_dir):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(archives_dir, filename)
                    os.remove(filepath)
                    deleted_files += 1
        
        logger.critical("✅ All archives deleted: %d files removed by admin %s", deleted_files, user_id)
        
        return JSONResponse(content={
            "success": True,
            "message": "Всі архіви видалено",
            "deleted_count": deleted_files
        })
    
    except Exception as e:
        logger.error("Помилка видалення архівів: %s", e, exc_info=True)
        return JSONResponse(
            content={"success": False, "message": f"Помилка: {str(e)}"},
            status_code=500
        )


@router.post("/danger/full-wipe")
async def danger_full_wipe(user_id: int = Query(...)):
    """
    🚨🚨🚨 НАЙКРИТИЧНІША ОПЕРАЦІЯ 🚨🚨🚨
    Повне очищення системи:
    - Всі товари з БД
    - Всі фото (файли + БД)
    - Всі архіви
    - Всі дані модерації
    
    НЕЗВОРОТНА ОПЕРАЦІЯ!
    """
    verify_admin(user_id)
    
    try:
        logger.critical("🚨🚨🚨 DANGER ZONE: User %s initiated FULL WIPE operation!", user_id)
        
        deleted_products = 0
        deleted_photo_files = 0
        deleted_photo_records = 0
        deleted_archives = 0
        
        async with async_session() as session:
            # 1. Products count
            result_products = await session.execute(text("SELECT COUNT(*) FROM products"))
            deleted_products = result_products.scalar()
            
            # 2. Photos (спочатку файли за file_path з правильним шляхом)
            result_photos = await session.execute(
                text("SELECT file_path FROM product_photos")
            )
            file_paths = [row[0] for row in result_photos.fetchall()]
            
            for relative_path in file_paths:
                try:
                    full_path = _BASE_DIR / "static" / relative_path
                    if full_path.exists():
                        full_path.unlink()
                        deleted_photo_files += 1
                except Exception as e:
                    logger.error(f"Error deleting photo file {full_path}: {e}")
            
            # 3. БД: product_photos спочатку, потім products
            delete_photos_result = await session.execute(text("DELETE FROM product_photos"))
            deleted_photo_records = delete_photos_result.rowcount
            await session.execute(text("DELETE FROM products"))
            await session.commit()
        
        # 4. Архіви
        archives_dir = os.path.join(ARCHIVES_PATH, "active")
        if os.path.exists(archives_dir):
            for filename in os.listdir(archives_dir):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(archives_dir, filename)
                    os.remove(filepath)
                    deleted_archives += 1
        
        logger.critical(
            "✅ FULL WIPE completed by admin %s: Products=%d, Photo files=%d, Photo records=%d, Archives=%d",
            user_id, deleted_products, deleted_photo_files, deleted_photo_records, deleted_archives
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "Повне очищення завершено",
            "deleted_products": deleted_products,
            "deleted_photos": deleted_photo_files,
            "deleted_photo_records": deleted_photo_records,
            "deleted_archives": deleted_archives
        })
    
    except Exception as e:
        logger.error("Помилка повного очищення: %s", e, exc_info=True)
        return JSONResponse(
            content={"success": False, "message": f"Помилка: {str(e)}"},
            status_code=500
        )


# ===========================================================================
# Mobile App (Android) Admin endpoint — JWT Bearer token authentication
# ===========================================================================

@router.get("/stats")
async def mobile_admin_stats(authorization: str = Header(...)):
    """
    GET /api/admin/stats
    Статистика системи для мобільного адмін-модуля (JWT-автентифікація).
    """
    from webapp.routers.auth import get_current_user
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Невірний формат заголовка Authorization")
    user_id = get_current_user(authorization[7:])

    user = await orm_get_user_by_id(user_id)
    if not user or user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Access denied. Admin rights required.")

    try:
        loop = asyncio.get_running_loop()
        all_users = await loop.run_in_executor(None, orm_get_all_users_sync)
        all_products = await loop.run_in_executor(None, orm_get_all_products_sync)
        active_users_data = await orm_get_users_with_active_lists()
        temp_list_items = await loop.run_in_executor(None, orm_get_all_temp_list_items_sync)

        pending_count = 0
        async with async_session() as session:
            from sqlalchemy import select as sa_select, func as sa_func
            from database.models import User as UserModel
            res = await session.execute(
                sa_select(sa_func.count()).select_from(UserModel).where(UserModel.status == "pending")
            )
            pending_count = res.scalar_one()

        total_reserved_sum = sum(
            item.quantity * (item.product.ціна or 0.0) for item in temp_list_items
        )

        return JSONResponse({
            "total_users": len(all_users),
            "active_users": len(active_users_data),
            "total_products": len(all_products),
            "pending_users": pending_count,
            "total_reserved_sum": round(total_reserved_sum, 2),
        })
    except Exception as e:
        logger.error("Помилка отримання статистики (mobile): %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Помилка отримання статистики")
