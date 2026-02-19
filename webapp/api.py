# webapp/api.py
"""
Головний FastAPI додаток для webapp.
Інтегрує клієнтські та адміністративні роутери.
"""

import os
import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Додаємо шлях до кореневої папки проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from webapp.routers import admin, client

# Створюємо FastAPI додаток
app = FastAPI(
    title="EpicService API",
    description="API для управління замовленнями та товарами",
    version="2.0.0"
)

# Статичні файли
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static"
)

# Шаблони
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

# Підключаємо роутери
app.include_router(
    client.router,
    prefix="/api",
    tags=["client"]
)

app.include_router(
    admin.router,
    prefix="/api/admin",
    tags=["admin"]
)


# === Загальні ендпоїнти ===

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Повертає 204 No Content щоб не була 404 в логах"""
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Головна сторінка Mini App"""
    # Читаємо список ID адмінів з .env
    admin_ids_str = os.getenv("WEBAPP_ADMIN_IDS", "")
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "admin_ids": admin_ids
    })


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Адмін-панель"""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/health")
async def health_check():
    """Перевірка стану API"""
    return {
        "status": "ok",
        "service": "epicservice",
        "version": "2.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True  # Автоперезавантаження під час розробки
    )
