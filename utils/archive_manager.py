# epicservice/utils/archive_manager.py

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

from config import ARCHIVES_PATH

logger = logging.getLogger(__name__)

ACTIVE_DIR = os.path.join(ARCHIVES_PATH, "active")
TRASH_DIR = os.path.join(ARCHIVES_PATH, "trash")


def ensure_archive_dirs():
    """
    Перевіряє наявність папок archives/active та archives/trash.
    Якщо немає — створює.
    """
    try:
        os.makedirs(ACTIVE_DIR, exist_ok=True)
        os.makedirs(TRASH_DIR, exist_ok=True)
        logger.info(f"Архівні директорії готові: {ACTIVE_DIR}, {TRASH_DIR}")
    except Exception as e:
        logger.error(f"Помилка створення архівних папок: {e}", exc_info=True)


def parse_filename(filename: str) -> dict | None:
    """
    Парсить назву файлу формату: {department}_{user_id}_{dd-mm-yyyy}_{hh-mm}.xlsx
    Повертає dict з полями: department, user_id, timestamp, filename
    """
    try:
        # Прибираємо префікс "лишки_" якщо є
        name = filename.replace("лишки_", "")
        
        # Видаляємо розширення
        name = name.replace(".xlsx", "")
        
        # Розбиваємо: department_user_id_dd-mm-yyyy_hh-mm
        parts = name.split("_")
        if len(parts) < 4:
            return None
        
        department = parts[0]
        user_id = int(parts[1])
        date_str = parts[2]  # dd-mm-yyyy
        time_str = parts[3]  # hh-mm
        
        # Парсимо дату
        timestamp = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H-%M")
        
        return {
            "department": department,
            "user_id": user_id,
            "timestamp": timestamp,
            "filename": filename
        }
    except Exception as e:
        logger.debug(f"Не вдалося розпарсити файл {filename}: {e}")
        return None


def get_user_archives(user_id: int) -> List[Tuple[str, datetime]]:
    """
    Повертає список файлів конкретного юзера з archives/active/.
    
    Returns:
        Список кортежів (filename, timestamp), відсортований за датою (новіші спочатку)
    """
    try:
        files = []
        for filename in os.listdir(ACTIVE_DIR):
            if not filename.endswith(".xlsx"):
                continue
            
            parsed = parse_filename(filename)
            if parsed and parsed["user_id"] == user_id:
                files.append((filename, parsed["timestamp"]))
        
        # Сортуємо за датою (новіші спочатку)
        files.sort(key=lambda x: x[1], reverse=True)
        return files
    except Exception as e:
        logger.error(f"Помилка отримання архівів для user_id={user_id}: {e}", exc_info=True)
        return []


def get_all_archives() -> List[Tuple[str, datetime, int]]:
    """
    Повертає всі файли з archives/active/ (для адміна).
    
    Returns:
        Список кортежів (filename, timestamp, user_id), відсортований за датою
    """
    try:
        files = []
        for filename in os.listdir(ACTIVE_DIR):
            if not filename.endswith(".xlsx"):
                continue
            
            parsed = parse_filename(filename)
            if parsed:
                files.append((filename, parsed["timestamp"], parsed["user_id"]))
        
        files.sort(key=lambda x: x[1], reverse=True)
        return files
    except Exception as e:
        logger.error(f"Помилка отримання всіх архівів: {e}", exc_info=True)
        return []


def rotate_user_files(user_id: int, limit: int = 10):
    """
    Ротація файлів юзера: залишає найновіші `limit` файлів,
    решту переміщує в trash/.
    """
    try:
        user_files = get_user_archives(user_id)
        
        if len(user_files) <= limit:
            return  # Ротація не потрібна
        
        # Файли, які треба перемістити в trash
        files_to_move = user_files[limit:]
        
        for filename, _ in files_to_move:
            src = os.path.join(ACTIVE_DIR, filename)
            dst = os.path.join(TRASH_DIR, filename)
            
            if os.path.exists(src):
                shutil.move(src, dst)
                logger.info(f"Переміщено в trash: {filename}")
        
        logger.info(f"Ротація для user_id={user_id}: переміщено {len(files_to_move)} файлів")
    except Exception as e:
        logger.error(f"Помилка ротації для user_id={user_id}: {e}", exc_info=True)


def cleanup_trash(days: int = 14):
    """
    Видаляє файли з trash/, які старіше вказаної кількості днів.
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for filename in os.listdir(TRASH_DIR):
            if not filename.endswith(".xlsx"):
                continue
            
            filepath = os.path.join(TRASH_DIR, filename)
            
            # Перевіряємо дату модифікації файлу
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            if file_mtime < cutoff_date:
                os.remove(filepath)
                deleted_count += 1
                logger.info(f"Видалено з trash: {filename}")
        
        if deleted_count > 0:
            logger.info(f"Очищення trash: видалено {deleted_count} файлів (старіше {days} днів)")
        else:
            logger.info("Очищення trash: немає файлів для видалення")
    except Exception as e:
        logger.error(f"Помилка очищення trash: {e}", exc_info=True)
