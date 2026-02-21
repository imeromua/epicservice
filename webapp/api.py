# webapp/api.py
"""
Головний FastAPI додаток для webapp.
Інтегрує клієнтські та адміністративні роутери.
"""

import os
import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Додаємо шлях до кореневої папки проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from webapp.routers import admin, client, photos

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

app.include_router(
    photos.router,
    prefix="/api",
    tags=["photos"]
)


# === Загальні ендпоїнти ===

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Повертає 204 No Content щоб не була 404 в логах"""
    return Response(status_code=204)


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    """Віддає Service Worker для PWA з кореня"""
    sw_path = os.path.join(os.path.dirname(__file__), "sw.js")
    response = FileResponse(sw_path, media_type="application/javascript")
    # Забороняємо кешування Service Worker
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
    """Адмін-панель - віддає статичний HTML файл без кешування"""
    admin_html_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    response = FileResponse(admin_html_path)
    # Забороняємо кешування
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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