from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import sys
import os
import traceback
from aiogram import Bot
from aiogram.types import FSInputFile

# Додаємо шлях до кореневої папки проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.engine import async_session
from database.orm import (
    orm_find_products, 
    orm_get_temp_list, 
    orm_add_item_to_temp_list,
    orm_update_temp_list_item_quantity,
    orm_delete_temp_list_item,
    orm_clear_temp_list
)
from utils.list_processor import process_and_save_list
from sqlalchemy.exc import SQLAlchemyError
from config import BOT_TOKEN

app = FastAPI()

# Статичні файли і шаблони
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Bot instance
bot = Bot(token=BOT_TOKEN)


class SearchRequest(BaseModel):
    query: str
    user_id: int


class AddToListRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int


class UpdateQuantityRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int


class DeleteItemRequest(BaseModel):
    user_id: int
    product_id: int


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Головна сторінка Mini App"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Перевірка стану API"""
    return {"status": "ok"}


@app.post("/api/search")
async def search_products(req: SearchRequest):
    """
    Пошук товарів за артикулом або назвою.
    Повертає список товарів з інформацією про наявність.
    """
    try:
        print(f"🔍 Search request: query='{req.query}', user_id={req.user_id}")
        
        print(f"📞 Calling orm_find_products...")
        products = await orm_find_products(req.query)
        print(f"✅ orm_find_products returned {len(products) if products else 0} products")
        
        if not products:
            print(f"⚠️ No products found")
            return JSONResponse(content={"products": [], "message": "Нічого не знайдено"}, status_code=200)
        
        # Формуємо відповідь
        result = []
        for product in products:
            # Розрахуємо доступну кількість
            try:
                total_quantity = float(product.кількість)
            except (ValueError, TypeError):
                total_quantity = 0.0
            
            available = total_quantity - product.відкладено
            
            result.append({
                "id": product.id,
                "article": product.артикул,
                "name": product.назва,
                "price": float(product.ціна),
                "available": available,
                "department": product.відділ
            })
        
        print(f"✅ Returning {len(result)} products")
        return JSONResponse(content={"products": result}, status_code=200)
        
    except SQLAlchemyError as e:
        print(f"❌ SQLAlchemy ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Помилка бази даних", "details": str(e)},
            status_code=500
        )
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Неочікувана помилка", "details": str(e)},
            status_code=500
        )


@app.get("/api/list/{user_id}")
async def get_user_list(user_id: int):
    """
    Отримати поточний список товарів користувача.
    """
    try:
        temp_list = await orm_get_temp_list(user_id)
        
        if not temp_list:
            return JSONResponse(content={"items": [], "total": 0}, status_code=200)
        
        items = []
        total_sum = 0.0
        
        for item in temp_list:
            item_total = float(item.product.ціна) * item.quantity
            total_sum += item_total
            
            items.append({
                "product_id": item.product.id,
                "article": item.product.артикул,
                "name": item.product.назва,
                "quantity": item.quantity,
                "price": float(item.product.ціна),
                "total": item_total
            })
        
        return JSONResponse(content={
            "items": items,
            "total": total_sum,
            "count": len(items)
        }, status_code=200)
        
    except Exception as e:
        return JSONResponse(
            content={"error": "Помилка отримання списку", "details": str(e)},
            status_code=500
        )


@app.post("/api/add")
async def add_to_list(req: AddToListRequest):
    """
    Додати товар до списку користувача.
    """
    try:
        print(f"➕ Add to list request: user_id={req.user_id}, product_id={req.product_id}, quantity={req.quantity}")
        
        print(f"📞 Calling orm_add_item_to_temp_list...")
        await orm_add_item_to_temp_list(
            user_id=req.user_id,
            product_id=req.product_id,
            quantity=req.quantity
        )
        print(f"✅ Successfully added to temp list")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Додано {req.quantity} шт."
        }, status_code=200)
                    
    except Exception as e:
        print(f"❌ ERROR in add_to_list: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Помилка додавання", "details": str(e)},
            status_code=500
        )


@app.post("/api/update")
async def update_item_quantity(req: UpdateQuantityRequest):
    """
    Оновити кількість товару в списку.
    """
    try:
        if req.quantity < 1:
            return JSONResponse(
                content={"success": False, "message": "Кількість має бути більше 0"},
                status_code=400
            )
        
        await orm_update_temp_list_item_quantity(
            user_id=req.user_id,
            product_id=req.product_id,
            new_quantity=req.quantity
        )
        
        return JSONResponse(content={
            "success": True,
            "message": f"Кількість оновлено: {req.quantity} шт."
        }, status_code=200)
                    
    except Exception as e:
        print(f"❌ ERROR in update_item_quantity: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Помилка оновлення", "details": str(e)},
            status_code=500
        )


@app.post("/api/delete")
async def delete_item(req: DeleteItemRequest):
    """
    Видалити товар зі списку.
    """
    try:
        await orm_delete_temp_list_item(
            user_id=req.user_id,
            product_id=req.product_id
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "Товар видалено"
        }, status_code=200)
                    
    except Exception as e:
        print(f"❌ ERROR in delete_item: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Помилка видалення", "details": str(e)},
            status_code=500
        )


@app.post("/api/clear/{user_id}")
async def clear_list(user_id: int):
    """
    Очистити весь список користувача.
    """
    try:
        await orm_clear_temp_list(user_id)
        
        return JSONResponse(content={
            "success": True,
            "message": "Список очищено"
        }, status_code=200)
                    
    except Exception as e:
        print(f"❌ ERROR in clear_list: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Помилка очищення", "details": str(e)},
            status_code=500
        )


@app.post("/api/save/{user_id}")
async def save_list_to_excel(user_id: int):
    """
    Зберегти список користувача в Excel та відправити в Telegram.
    Використовує ту саму логіку що й бот: 
    - Зберігає в archives/active/
    - Розділяє на основний список та лишки
    - Резервує товари в БД
    - Очищає тимчасовий список
    """
    try:
        print(f"💾 Save list request for user_id={user_id}")
        
        async with async_session() as session:
            async with session.begin():
                # Використовуємо ту саму функцію що й бот
                main_list_path, surplus_list_path = await process_and_save_list(session, user_id)
        
        if not main_list_path and not surplus_list_path:
            print(f"⚠️ List is empty for user {user_id}")
            return JSONResponse(
                content={"success": False, "message": "Список порожній"},
                status_code=400
            )
        
        print(f"✅ Files saved: main={main_list_path}, surplus={surplus_list_path}")
        
        # Відправка файлів через бота
        try:
            if main_list_path:
                document = FSInputFile(main_list_path)
                await bot.send_document(
                    chat_id=user_id,
                    document=document,
                    caption="📋 Ваш основний список збережено"
                )
                print(f"📤 Main list sent to user {user_id}")
            
            if surplus_list_path:
                document = FSInputFile(surplus_list_path)
                await bot.send_document(
                    chat_id=user_id,
                    document=document,
                    caption="📦 Лишки (товарів не вистачило)"
                )
                print(f"📤 Surplus list sent to user {user_id}")
            
            return JSONResponse(content={
                "success": True,
                "message": "Список збережено та відправлено в чат!",
                "cleared": True  # Сигнал для фронтенду що треба очистити UI
            }, status_code=200)
            
        except Exception as bot_error:
            print(f"❌ Error sending file via bot: {bot_error}")
            traceback.print_exc()
            return JSONResponse(
                content={"success": False, "message": "Помилка відправки файлу"},
                status_code=500
            )
                    
    except Exception as e:
        print(f"❌ ERROR in save_list_to_excel: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Помилка збереження списку", "details": str(e)},
            status_code=500
        )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
