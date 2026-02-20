# webapp/routers/admin.py
"""
Адміністративний роутер для управління системою через веб-інтерфейс.
Містить ендпоїнти для імпорту/експорту даних, управління користувачами та звітів.
"""

import asyncio
import logging
import os
import tempfile
import zipfile
from datetime import datetime
from typing import List, Optional

import openpyxl
import pandas as pd
from aiogram import Bot
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from config import ADMIN_IDS, ARCHIVES_PATH, BOT_TOKEN
from database.orm import (
    orm_get_all_collected_items_sync,
    orm_get_all_products_sync,
    orm_get_all_temp_list_items_sync,
    orm_get_all_users_sync,
    orm_get_users_with_active_lists,
    orm_smart_import,
    orm_subtract_collected,
)
from database.orm.products import SmartColumnMapper
from keyboards.inline import get_admin_main_kb
from lexicon.lexicon import LEXICON
from utils.force_save_helper import force_save_user_list_web

logger = logging.getLogger(__name__)
router = APIRouter()
bot = Bot(token=BOT_TOKEN)


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


# === Pydantic Models ===

class AdminActionRequest(BaseModel):
    user_id: int
    action: str  # 'notify' або 'force_save'


class BroadcastRequest(BaseModel):
    user_id: int
    message: str


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
    """Створює звіт про залишки на складі."""
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
    """Розсилає повідомлення всім користувачам про оновлення бази товарів."""
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

        sent_count = 0
        for user_id in user_ids:
            try:
                kb = get_admin_main_kb()
                await bot.send_message(user_id, message_text, reply_markup=kb, parse_mode='HTML')
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
        
        # Групуємо по користувачах
        user_data = {}
        for item in temp_list_items:
            if item.user_id not in user_data:
                user_data[item.user_id] = {
                    "user_id": item.user_id,
                    "username": f"User {item.user_id}",
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
    verify_admin(user_id)
    
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


@router.get("/export/stock")
async def export_stock_report(user_id: int = Query(...), background_tasks: BackgroundTasks = None):
    """
    Експорт звіту про залишки на складі.
    Враховує резерви з temp_list.
    """
    verify_admin(user_id)
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
    request: dict
):
    """
    Примусово зберегти список користувача.
    Використовується перед важливими операціями (імпорт, експорт).
    """
    user_id = request.get("user_id")
    verify_admin(user_id)
    
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
            
            users_data.append({
                "user_id": uid,
                "username": f"User {uid}",
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
    Отримати інформацію про товари: кількість артикулів, сума, розбивка по відділах.
    Враховує тільки доступні товари (кількість > 0 після резерву).
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
        
        # Фільтруємо тільки товари з доступною кількістю > 0
        available_products = []
        dept_stats = {}
        total_sum = 0.0
        
        for product in all_products:
            try:
                stock_qty = float(str(product.кількість).replace(',', '.'))
            except (ValueError, TypeError):
                stock_qty = 0
            
            # Рахуємо доступну кількість (залишок - резерв)
            reserved = (product.відкладено or 0) + temp_reservations.get(product.id, 0)
            available = stock_qty - reserved
            
            # ✅ Враховуємо тільки товари з доступною кількістю > 0
            if available > 0:
                available_products.append(product)
                dept = product.відділ
                dept_stats[dept] = dept_stats.get(dept, 0) + 1
                total_sum += available * (product.ціна or 0.0)
        
        departments = [
            {"department": dept_id, "count": count}
            for dept_id, count in sorted(dept_stats.items())
        ]
        
        # Остання дата імпорту (з першого товару)
        last_import = None
        if all_products and hasattr(all_products[0], 'created_at'):
            last_import = all_products[0].created_at.strftime('%d.%m - %H:%M')
        
        return JSONResponse(content={
            "success": True,
            "total_articles": len(available_products),  # ✅ Тільки доступні
            "total_sum": round(total_sum, 2),           # ✅ Сума доступних
            "departments": departments,                  # ✅ По відділах
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
