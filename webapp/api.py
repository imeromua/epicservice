# epicservice/webapp/api.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import sys
import os

# Додаємо шлях до кореневої папки проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.engine import async_session
from database.orm import orm_search_products, orm_get_temp_list, orm_add_to_temp_list
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

# Статичні файли і шаблони
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


class SearchRequest(BaseModel):
    query: str
    user_id: int


class AddToListRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int


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
        async with async_session() as session:
            products = await orm_search_products(req.query, session=session)
            
            if not products:
                return JSONResponse(content={"products": [], "message": "Нічого не знайдено"}, status_code=200)
            
            # Формуємо відповідь
            result = []
            for product in products:
                result.append({
                    "id": product.id,
                    "article": product.артикул,
                    "name": product.назва,
                    "price": float(product.ціна),
                    "available": product.доступна_кількість,
                    "department": product.відділ
                })
            
            return JSONResponse(content={"products": result}, status_code=200)
            
    except SQLAlchemyError as e:
        return JSONResponse(
            content={"error": "Помилка бази даних", "details": str(e)},
            status_code=500
        )
    except Exception as e:
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
        async with async_session() as session:
            temp_list = await orm_get_temp_list(user_id, session=session)
            
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
        async with async_session() as session:
            async with session.begin():
                result = await orm_add_to_temp_list(
                    user_id=req.user_id,
                    product_id=req.product_id,
                    quantity=req.quantity,
                    session=session
                )
                
                if result:
                    return JSONResponse(content={
                        "success": True,
                        "message": f"Додано {req.quantity} шт."
                    }, status_code=200)
                else:
                    return JSONResponse(content={
                        "success": False,
                        "message": "Не вдалося додати товар"
                    }, status_code=400)
                    
    except Exception as e:
        return JSONResponse(
            content={"error": "Помилка додавання", "details": str(e)},
            status_code=500
        )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
