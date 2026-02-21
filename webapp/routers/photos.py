"""API endpoints for product photo management."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pathlib import Path
from typing import List
import shutil
from datetime import datetime

from sqlalchemy.orm import Session
from database.database import get_db
from database.models import ProductPhoto, Product, User
from webapp.utils.image_processing import compress_image

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.post("/upload")
async def upload_photo(
    photo: UploadFile = File(...),
    article: str = Form(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload product photo.
    Maximum 3 photos per product.
    Photos are compressed to ~500KB.
    """
    # Verify product exists
    product = db.query(Product).filter(Product.артикул == article).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check existing photos count
    existing_count = db.query(ProductPhoto).filter(
        ProductPhoto.артикул == article,
        ProductPhoto.status.in_(['pending', 'approved'])
    ).count()
    
    if existing_count >= 3:
        return {
            "success": False,
            "message": "Максимум 3 фото на товар"
        }
    
    # Validate file type
    if not photo.content_type.startswith('image/'):
        return {
            "success": False,
            "message": "Неправильний тип файлу. Оберіть зображення."
        }
    
    # Create temp directory
    temp_dir = Path("webapp/temp_files")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Save temp file
    temp_path = temp_dir / f"temp_{user_id}_{photo.filename}"
    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        
        # Compress image
        compressed = compress_image(
            str(temp_path),
            article,
            existing_count
        )
        
        # Save to database
        new_photo = ProductPhoto(
            артикул=article,
            file_path=compressed['file_path'],
            file_size=compressed['file_size'],
            original_size=compressed['original_size'],
            photo_order=existing_count,
            uploaded_by=user_id,
            uploaded_at=datetime.now(),
            status='pending'
        )
        db.add(new_photo)
        db.commit()
        
        # Get approved photos for this product
        approved_photos = db.query(ProductPhoto).filter(
            ProductPhoto.артикул == article,
            ProductPhoto.status == 'approved'
        ).order_by(ProductPhoto.photo_order).all()
        
        photo_files = [p.file_path.split('/')[-1] for p in approved_photos]
        
        return {
            "success": True,
            "message": "Фото надіслано на модерацію",
            "photos": photo_files
        }
        
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.get("/product/{article}")
async def get_product_photos(
    article: str,
    db: Session = Depends(get_db)
):
    """
    Get all approved photos for a product.
    """
    photos = db.query(ProductPhoto).filter(
        ProductPhoto.артикул == article,
        ProductPhoto.status == 'approved'
    ).order_by(ProductPhoto.photo_order).all()
    
    return {
        "success": True,
        "photos": [
            {
                "id": p.id,
                "file_path": p.file_path,
                "order": p.photo_order
            } for p in photos
        ]
    }


@router.get("/moderation/pending")
async def get_pending_photos(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all photos pending moderation (admin only).
    """
    photos = db.query(ProductPhoto).filter(
        ProductPhoto.status == 'pending'
    ).order_by(ProductPhoto.uploaded_at.desc()).all()
    
    result = []
    for p in photos:
        product = db.query(Product).filter(Product.артикул == p.артикул).first()
        uploader = db.query(User).filter(User.id == p.uploaded_by).first()
        
        result.append({
            "id": p.id,
            "article": p.артикул,
            "product_name": product.назва if product else "",
            "file_path": p.file_path,
            "file_size": p.file_size,
            "original_size": p.original_size,
            "uploaded_by": uploader.username if uploader and uploader.username else f"ID {p.uploaded_by}",
            "uploaded_at": p.uploaded_at.strftime("%d.%m.%Y %H:%M")
        })
    
    return {
        "success": True,
        "photos": result
    }


@router.post("/moderation/{photo_id}")
async def moderate_photo(
    photo_id: int,
    status: str = Form(...),  # 'approved' or 'rejected'
    reason: str = Form(None),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Moderate photo (approve or reject).
    """
    photo = db.query(ProductPhoto).filter(ProductPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    photo.status = status
    photo.moderated_by = user_id
    photo.moderated_at = datetime.now()
    
    if status == 'rejected' and reason:
        photo.rejection_reason = reason
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Фото {'schvaleno' if status == 'approved' else 'відхилено'}"
    }


@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete photo (admin or uploader only).
    """
    photo = db.query(ProductPhoto).filter(ProductPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Delete file
    file_path = Path("webapp/static") / photo.file_path
    if file_path.exists():
        file_path.unlink()
    
    # Delete from DB
    db.delete(photo)
    db.commit()
    
    return {
        "success": True,
        "message": "Фото видалено"
    }
