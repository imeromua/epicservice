"""API endpoints for product photo management."""

import shutil
import traceback
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select

from database.engine import async_session
from database.models import ProductPhoto, Product, User
from webapp.utils.image_processing import compress_image

# prefix="/photos" + include_router prefix="/api"  =>  "/api/photos/..."
router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/upload")
async def upload_photo(
    photo: UploadFile = File(...),
    article: str = Form(...),
    user_id: int = Form(...),
):
    """
    Завантаження фото товару. Максимум 3 фото, автостискання до ~500KB.
    Завжди повертає JSON.
    """
    try:
        async with async_session() as session:
            # Перевірка існування товару
            prod_result = await session.execute(
                select(Product).where(Product.артикул == article)
            )
            product = prod_result.scalar_one_or_none()
            if not product:
                return JSONResponse(
                    content={"success": False, "message": "Товар не знайдено"},
                    status_code=404
                )

            # Кількість фото
            existing_result = await session.execute(
                select(ProductPhoto).where(
                    ProductPhoto.артикул == article,
                    ProductPhoto.status.in_(['pending', 'approved'])
                )
            )
            existing = existing_result.scalars().all()

            if len(existing) >= 3:
                return JSONResponse(content={
                    "success": False,
                    "message": "Максимум 3 фото на товар"
                })

            # Тип файлу
            if not photo.content_type or not photo.content_type.startswith('image/'):
                return JSONResponse(content={
                    "success": False,
                    "message": "Неправильний тип файлу. Оберіть зображення."
                })

            # Тимчасова директорія
            temp_dir = Path(__file__).resolve().parent.parent / "temp_files"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / f"temp_{user_id}_{photo.filename}"

            try:
                with temp_path.open("wb") as buffer:
                    shutil.copyfileobj(photo.file, buffer)

                # Стискання
                compressed = compress_image(str(temp_path), article, len(existing))

                # Збереження в БД
                new_photo = ProductPhoto(
                    артикул=article,
                    file_path=compressed['file_path'],
                    file_size=compressed['file_size'],
                    original_size=compressed['original_size'],
                    photo_order=len(existing),
                    uploaded_by=user_id,
                    uploaded_at=datetime.now(),
                    status='pending'
                )
                session.add(new_photo)
                await session.commit()

                # Схвалені фото
                approved_result = await session.execute(
                    select(ProductPhoto).where(
                        ProductPhoto.артикул == article,
                        ProductPhoto.status == 'approved'
                    ).order_by(ProductPhoto.photo_order)
                )
                approved = approved_result.scalars().all()

                return JSONResponse(content={
                    "success": True,
                    "message": "Фото надіслано на модерацію",
                    "photos": [p.file_path.split('/')[-1] for p in approved]
                })

            finally:
                if temp_path.exists():
                    temp_path.unlink()

    except Exception as e:
        print(f"❌ ERROR in upload_photo: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"success": False, "message": f"Помилка сервера: {str(e)}"},
            status_code=500
        )


@router.get("/product/{article}")
async def get_product_photos(article: str):
    """Approved фото для візуалізації."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(ProductPhoto).where(
                    ProductPhoto.артикул == article,
                    ProductPhoto.status == 'approved'
                ).order_by(ProductPhoto.photo_order)
            )
            photos = result.scalars().all()

            return JSONResponse(content={
                "success": True,
                "photos": [
                    {"id": p.id, "file_path": p.file_path, "order": p.photo_order}
                    for p in photos
                ]
            })
    except Exception as e:
        print(f"❌ ERROR in get_product_photos: {e}")
        return JSONResponse(content={"success": False, "photos": []}, status_code=500)


@router.get("/moderation/pending")
async def get_pending_photos(user_id: int):
    """Фото на модерації (тільки адмін)."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(ProductPhoto).where(
                    ProductPhoto.status == 'pending'
                ).order_by(ProductPhoto.uploaded_at.desc())
            )
            photos = result.scalars().all()

            result_list = []
            for p in photos:
                prod_res = await session.execute(
                    select(Product).where(Product.артикул == p.артикул)
                )
                product = prod_res.scalar_one_or_none()

                user_res = await session.execute(
                    select(User).where(User.id == p.uploaded_by)
                )
                uploader = user_res.scalar_one_or_none()

                result_list.append({
                    "id": p.id,
                    "article": p.артикул,
                    "product_name": product.назва if product else "",
                    "file_path": p.file_path,
                    "file_size": p.file_size,
                    "original_size": p.original_size,
                    "uploaded_by": uploader.username if uploader and uploader.username else f"ID {p.uploaded_by}",
                    "uploaded_at": p.uploaded_at.strftime("%d.%m.%Y %H:%M")
                })

            return JSONResponse(content={"success": True, "photos": result_list})
    except Exception as e:
        print(f"❌ ERROR in get_pending_photos: {e}")
        return JSONResponse(content={"success": False, "photos": []}, status_code=500)


@router.post("/moderation/{photo_id}")
async def moderate_photo(
    photo_id: int,
    status: str = Form(...),
    reason: str = Form(None),
    user_id: int = Form(...),
):
    """Модерація: схвалити або відхилити."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(ProductPhoto).where(ProductPhoto.id == photo_id)
            )
            photo = result.scalar_one_or_none()

            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")

            photo.status = status
            photo.moderated_by = user_id
            photo.moderated_at = datetime.now()

            if status == 'rejected' and reason:
                photo.rejection_reason = reason

            await session.commit()

            return JSONResponse(content={
                "success": True,
                "message": "Фото схвалено" if status == 'approved' else "Фото відхилено"
            })
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR in moderate_photo: {e}")
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)


@router.delete("/{photo_id}")
async def delete_photo(photo_id: int, user_id: int):
    """Видалення фото (адмін або автор)."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(ProductPhoto).where(ProductPhoto.id == photo_id)
            )
            photo = result.scalar_one_or_none()

            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")

            # Видаляємо фізичний файл
            # photo.file_path вже містить "uploads/photos/filename.jpg"
            webapp_root = Path(__file__).resolve().parent.parent
            full_file_path = webapp_root / "static" / photo.file_path
            
            if full_file_path.exists():
                full_file_path.unlink()
                print(f"✅ Фото видалено: {full_file_path}")
            else:
                print(f"⚠️ Файл не знайдено: {full_file_path}")

            # Видаляємо запис з БД
            await session.delete(photo)
            await session.commit()

            return JSONResponse(content={"success": True, "message": "Фото видалено"})
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR in delete_photo: {e}")
        traceback.print_exc()
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=500)
