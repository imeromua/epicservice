"""Utility for image compression and processing."""

from PIL import Image
import os
from pathlib import Path
from typing import Dict

# Configuration
UPLOAD_DIR = Path("webapp/static/uploads/photos")
MAX_DIMENSION = 1200  # Maximum side size in pixels
TARGET_FILE_SIZE = 500 * 1024  # 500 KB target
QUALITY_START = 95
QUALITY_MIN = 50


def compress_image(input_path: str, article: str, order: int) -> Dict:
    """
    Compress image by size while maintaining quality.
    
    Args:
        input_path: Path to the original image
        article: Product article (folder name)
        order: Photo order number (0-2)
    
    Returns:
        dict: {
            'file_path': relative path to compressed image,
            'file_size': size after compression in bytes,
            'original_size': original file size in bytes
        }
    """
    img = Image.open(input_path)
    original_size = os.path.getsize(input_path)
    
    # Convert RGBA/LA/P to RGB (for JPEG)
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img)
        img = background
    
    # Resize if too large
    if max(img.size) > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
    
    # Create output directory
    output_dir = UPLOAD_DIR / article
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"photo_{order}.jpg"
    
    # Progressive quality reduction until target size is reached
    quality = QUALITY_START
    while quality >= QUALITY_MIN:
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        file_size = os.path.getsize(output_path)
        
        if file_size <= TARGET_FILE_SIZE:
            break
        
        quality -= 5
    
    # Return relative path from static directory
    relative_path = str(output_path.relative_to("webapp/static"))
    
    return {
        'file_path': relative_path,
        'file_size': file_size,
        'original_size': original_size
    }


def delete_product_photos(article: str) -> None:
    """
    Delete all photos for a product.
    
    Args:
        article: Product article
    """
    photo_dir = UPLOAD_DIR / article
    if photo_dir.exists():
        for file in photo_dir.glob("*"):
            file.unlink()
        photo_dir.rmdir()
