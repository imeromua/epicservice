"""Utility for image compression and processing."""

from PIL import Image
import os
from pathlib import Path
from typing import Dict

# Абсолютний шлях відносно цього файлу — не залежить від CWD
_BASE_DIR = Path(__file__).resolve().parent.parent  # webapp/
UPLOAD_DIR = _BASE_DIR / "static" / "uploads" / "photos"

MAX_DIMENSION = 1200        # Максимальний розмір сторони в пікселях
TARGET_FILE_SIZE = 500 * 1024  # 500 KB
QUALITY_START = 95
QUALITY_MIN = 50


def compress_image(input_path: str, article: str, order: int) -> Dict:
    """
    Стискає зображення зі збереженням якості.

    Args:
        input_path: Шлях до оригінального файлу
        article: Артикул товару (назва папки)
        order: Порядковий номер фото (0–2)

    Returns:
        dict: file_path (відносно static/), file_size, original_size
    """
    img = Image.open(input_path)
    original_size = os.path.getsize(input_path)

    # Конвертуємо в RGB для JPEG
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Зменшуємо якщо занадто велике
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    # Створюємо директорію для товару
    output_dir = UPLOAD_DIR / article
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"photo_{order}.jpg"

    # Поступово знижуємо якість до досягнення цільового розміру
    quality = QUALITY_START
    file_size = 0
    while quality >= QUALITY_MIN:
        img.save(str(output_path), 'JPEG', quality=quality, optimize=True)
        file_size = os.path.getsize(str(output_path))
        if file_size <= TARGET_FILE_SIZE:
            break
        quality -= 5

    # Відносний шлях від webapp/static/
    static_dir = _BASE_DIR / "static"
    relative_path = str(output_path.relative_to(static_dir))

    return {
        'file_path': relative_path,
        'file_size': file_size,
        'original_size': original_size
    }


def delete_product_photos(article: str) -> None:
    """Видалити всі фото товару."""
    photo_dir = UPLOAD_DIR / article
    if photo_dir.exists():
        for file in photo_dir.glob("*"):
            file.unlink()
        photo_dir.rmdir()
