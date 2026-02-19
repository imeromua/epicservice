# 🛠️ Технічний посібник EpicService

**Версія:** 2.0.0  
**Останнє оновлення:** 19.02.2026

Цей документ надає поглиблений технічний огляд EpicService, призначений для розробників, DevOps-інженерів та системних адміністраторів.

---

## 📚 Зміст

1. [Архітектура системи](#1-архітектура-системи)
2. [Технологічний стек](#2-технологічний-стек)
3. [Схема бази даних](#3-схема-бази-даних)
4. [Backend (Telegram Bot)](#4-backend-telegram-bot)
5. [WebApp (Mini App + PWA)](#5-webapp-mini-app--pwa)
6. [Ключові бізнес-процеси](#6-ключові-бізнес-процеси)
7. [API документація](#7-api-документація)
8. [Розгортання](#8-розгортання)
9. [Моніторинг та логування](#9-моніторинг-та-логування)
10. [Безпека](#10-безпека)
11. [Продуктивність](#11-продуктивність)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Архітектура системи

### 1.1 Компоненти системи

```
┌───────────────────────┐
│   Користувачі        │
│  (Telegram Client)  │
└─────────┬────────────┘
         │
    ┌────┼────┐
    │         │
┌───┴────┐ ┌─┴───────────────┐
│ Bot API │ │ WebApp (PWA)     │
│ aiogram │ │ FastAPI + HTML   │
└───┬────┘ └─┬──────────────┘
    │         │
    └───┬────┤
        │    │ Service Worker
    ┌───┼────┤ (Offline Cache)
    │   │    └───────────┐
┌───┴───┼────────────────┐ │
│ PostgreSQL         │ │
│ (Основні дані)   │ │
└─────────┬─────────┘ │
          │            │
     ┌────┼────┐       │
     │ Redis    │       │
     │ (FSM)    │       │
     └─────────┘       │
                        │
     ┌─────────────────┴┐
     │ LocalStorage     │
     │ IndexedDB        │
     │ (Клієнтський)  │
     └──────────────────┘
```

### 1.2 Потік даних

1. **Користувач → Telegram Bot:**
   - Команди `/start`, `/admin`
   - Persistent клавіатура (кнопка "Адмінка")
   - Callback queries (інлайн кнопки)

2. **Користувач → WebApp:**
   - Відкривається через `web_app` кнопку в боті
   - PWA: можна встановити як додаток
   - REST API клики до FastAPI

3. **Bot/WebApp → PostgreSQL:**
   - Async ORM (SQLAlchemy 2.0)
   - Записи транзакцій
   - `FOR UPDATE` locks для резервів

4. **Bot → Redis:**
   - FSM states (стани користувачів)
   - Тимчасовий кеш

5. **PWA → LocalStorage/Service Worker:**
   - Кешування статичних ресурсів
   - Офлайн-режим
   - Налаштування UI

---

## 2. Технологічний стек

### 2.1 Backend

| Компонент | Технологія | Версія |
|------------|--------------|--------|
| **Мова** | Python | 3.11+ |
| **Bot Framework** | aiogram | 3.x |
| **Web Framework** | FastAPI | 0.100+ |
| **ORM** | SQLAlchemy | 2.0 |
| **БД** | PostgreSQL | 14+ |
| **Кеш** | Redis | 7+ |
| **Міграції** | Alembic | 1.x |
| **Async driver** | asyncpg | - |
| **Excel** | openpyxl | - |
| **Scheduler** | APScheduler | 3.x |

### 2.2 Frontend

| Компонент | Технологія |
|------------|---------------|
| **JS Framework** | Vanilla JS (ES6+) |
| **UI** | Telegram WebApp SDK |
| **PWA** | Service Worker API |
| **Стилі** | CSS Variables (темування) |
| **Офлайн** | Cache API + IndexedDB |
| **Templates** | Jinja2 |

### 2.3 DevOps

- **OS:** Ubuntu 22.04 LTS
- **Process Manager:** systemd
- **Web Server:** nginx (reverse proxy)
- **SSL/TLS:** Let's Encrypt (Certbot)
- **Version Control:** Git + GitHub
- **CI/CD:** Manual deployment (ready for GitHub Actions)

---

## 3. Схема бази даних

### 3.1 ER-діаграма

```
┌──────────────────┐
│      User          │
├──────────────────┤
│ id (PK)           │
│ username          │
│ first_name        │
│ last_name         │
│ created_at        │
└─────┬─────────────┘
     │
     │ 1:N
     │
┌────┼────────────────┐
│    TempList          │
├────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ product_id (FK) ───┬───────────────────┐
│ quantity            │ ┌───────────────────────┤
│ created_at          │ │       Product        │
└────────────────────┘ ├───────────────────────┤
                         │ id (PK)              │
┌────────────────────┐ │ article (UNIQUE)     │
│    SavedList        │ │ name                 │
├────────────────────┤ │ department           │
│ id (PK)            │ │ group_name           │
│ user_id (FK)       │ │ price                │
│ filename           │ │ available            │
│ filepath           │ │ reserved (резерв)  │
│ created_at         │ │ no_movement          │
└───┬─────────────────┘ │ is_active            │
   │                    │ updated_at           │
   │ 1:N                └───────────────────────┘
   │
┌──┼────────────────────┐
│  SavedListItem       │
├──────────────────────┤
│ id (PK)             │
│ saved_list_id (FK)  │
│ product_id (FK)     │
│ quantity            │
│ price               │
└──────────────────────┘
```

### 3.2 Основні таблиці

#### **User**
Зберігає інформацію про користувачів Telegram.
- `id` — Telegram User ID (Primary Key)
- `username`, `first_name`, `last_name` — з Telegram
- `created_at` — дата першого входу

#### **Product**
Каталог товарів.
- `id` — внутрішній ID
- `article` — унікальний артикул (UNIQUE INDEX)
- `name`, `department`, `group_name` — описові поля
- `price`, `available` — ціна та доступна кількість
- `reserved` — зарезервована кількість (для блокування)
- `no_movement` — без руху (діагностика)
- `is_active` — м'яке видалення

#### **TempList**
Поточні (незбережені) списки користувачів.
- `user_id` + `product_id` — composite key
- `quantity` — кількість у списку

**Логіка:** При додаванні товару в список → `product.reserved += quantity`

#### **SavedList / SavedListItem**
Збережені списки та їхні позиції.
- Зберігаються після натискання "💾 Зберегти"
- `filename` / `filepath` — Excel файл у `archives/active/`
- Використовується для статистики

---

## 4. Backend (Telegram Bot)

### 4.1 Структура проекту

```python
bot.py                    # Точка входу
config.py                 # Конфігурація (.env)

database/
  engine.py              # Async/Sync engine
  models.py              # SQLAlchemy models
  orm.py                 # ORM queries

handlers/
  common.py              # /start, персистент клавіатура
  webapp_handler.py      # Обробка webapp_data
  error_handler.py       # Глобальні помилки
  admin/
    core.py              # Основні адмін-команди
    import_handlers.py   # Імпорт Excel
    report_handlers.py   # Звіти
    archive_handlers.py  # Архіви

keyboards/
  inline.py              # Inline keyboards
  reply.py               # Reply keyboards

middlewares/
  logging_middleware.py  # Логування

utils/
  list_processor.py      # Створення Excel
  archive_manager.py     # Ротація файлів
  admin_helpers.py       # Admin utilities

lexicon/
  lexicon.py             # Текстові константи
```

### 4.2 FSM (Машина станів)

```python
from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_file = State()         # Очікуємо Excel
    waiting_for_confirmation = State() # Підтвердження імпорту
```

**Зберігається в Redis** з TTL.

### 4.3 Основні хендлери

#### **`/start`**
```python
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await orm_add_user(user_id, ...)
    
    # Persistent keyboard
    keyboard = get_persistent_keyboard(user_id)
    
    # WebApp button
    webapp_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🌐 Відкрити додаток",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]]
    )
```

#### **webapp_data handler**
Обробляє дані з WebApp:
```python
@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    data = json.loads(message.web_app_data.data)
    
    if data['action'] == 'save_list':
        # Зберегти список
        await process_and_save_list(data['user_id'])
```

---

## 5. WebApp (Mini App + PWA)

### 5.1 Архітектура

```
webapp/
  api.py                 # FastAPI додаток
  routers/
    client.py            # User endpoints
    admin.py             # Admin endpoints
  templates/
    index.html           # SPA frontend
  static/
    manifest.json        # PWA manifest
    sw.js                # Service Worker
    pwa-install.js       # Інсталяція PWA
    pwa-redirect.js      # Редирект логіка
    pwa-styles.css       # PWA стилі
    admin.html           # Адмін-панель
    icons/               # App icons
```

### 5.2 Service Worker

**Стратегія:** Cache First + Network Fallback

```javascript
// sw.js
const CACHE_NAME = 'epicservice-v2.0.0';

const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  '/static/pwa-styles.css',
  '/static/icons/icon-192x192.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
```

### 5.3 API Endpoints

#### **Client API** (`/api/*`)

| Method | Endpoint | Опис |
|--------|----------|------|
| POST | `/api/search` | Пошук товарів |
| GET | `/api/list/{user_id}` | Поточний список |
| POST | `/api/add` | Додати товар |
| POST | `/api/update` | Оновити кількість |
| POST | `/api/delete` | Видалити товар |
| POST | `/api/save/{user_id}` | Зберегти список |
| POST | `/api/clear/{user_id}` | Очистити список |
| GET | `/api/archives/{user_id}` | Архіви |
| GET | `/api/archives/download-all/{user_id}` | ZIP експорт |
| GET | `/api/statistics/{user_id}` | Статистика |

#### **Admin API** (`/api/admin/*`)

| Method | Endpoint | Опис |
|--------|----------|------|
| GET | `/api/admin/statistics` | Загальна статистика |
| POST | `/api/admin/import` | Імпорт Excel |
| GET | `/api/admin/export/stock` | Експорт залишків |
| POST | `/api/admin/force-save/{user_id}` | Примусове збереження |
| POST | `/api/admin/broadcast` | Розсилка |
| GET | `/api/admin/users/all` | Всі користувачі |
| GET | `/api/admin/archives/download-all` | ZIP всіх архівів |

---

## 6. Ключові бізнес-процеси

### 6.1 Резервування товарів

```python
async def add_to_list(user_id: int, product_id: int, quantity: int):
    async with async_session_maker() as session:
        async with session.begin():
            # 1. Додаємо в TempList
            await session.execute(
                insert(TempList).values(
                    user_id=user_id,
                    product_id=product_id,
                    quantity=quantity
                )
            )
            
            # 2. Резервуємо в Product
            await session.execute(
                update(Product)
                .where(Product.id == product_id)
                .values(reserved=Product.reserved + quantity)
            )
```

### 6.2 Блокування відділів

Логіка в `client.py` (`/api/search`):

```python
# Перший товар у списку визначає відділ
current_department = await get_user_current_department(user_id)

for product in products:
    product['is_different_department'] = (
        current_department is not None and 
        product['department'] != current_department
    )
```

**Frontend:**
```javascript
if (product.is_different_department) {
  card.classList.add('locked');
  card.onclick = null; // Блокуємо клік
}
```

### 6.3 Збереження списку

```python
async def process_and_save_list(user_id: int):
    async with async_session_maker() as session:
        async with session.begin():
            # 1. Отримуємо список
            temp_list = await get_temp_list(user_id)
            
            # 2. Генеруємо Excel
            filename = f"{user_id}_{timestamp}.xlsx"
            create_excel(temp_list, filename)
            
            # 3. Зберігаємо в SavedList
            saved_list = SavedList(
                user_id=user_id,
                filename=filename,
                filepath=f"archives/active/{user_id}/{filename}"
            )
            session.add(saved_list)
            
            # 4. Звільняємо резерви
            for item in temp_list:
                await session.execute(
                    update(Product)
                    .where(Product.id == item.product_id)
                    .values(reserved=Product.reserved - item.quantity)
                )
            
            # 5. Очищуємо TempList
            await session.execute(
                delete(TempList).where(TempList.user_id == user_id)
            )
```

### 6.4 Ротація файлів

**APScheduler задача (щоденно о 03:00):**

```python
from utils.archive_manager import rotate_user_archives

def cleanup_job():
    for user_id in get_all_user_ids():
        rotate_user_archives(user_id, keep_count=10)
    
    cleanup_trash(days=14)

scheduler.add_job(
    cleanup_job,
    'cron',
    hour=3,
    minute=0
)
```

---

## 7. API документація

### 7.1 Swagger UI

Автогенерована документація:
- http://localhost:8000/docs
- http://localhost:8000/redoc

### 7.2 Приклад запиту

#### **POST /api/search**

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "12345",
    "user_id": 123456789
  }'
```

**Response:**
```json
{
  "products": [
    {
      "id": 1,
      "article": "12345",
      "name": "Назва товару",
      "department": "Відділ A",
      "price": 100.50,
      "available": 10,
      "reserved": 2,
      "is_different_department": false
    }
  ]
}
```

---

## 8. Розгортання

### 8.1 Вимоги

- Ubuntu 22.04 LTS
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- nginx
- SSL certificate (Let's Encrypt)

### 8.2 Покрокова інструкція

```bash
# 1. Клонування
git clone https://github.com/imeromua/epicservice.git
cd epicservice

# 2. Віртуальне оточення
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. PostgreSQL
sudo -u postgres psql
CREATE DATABASE epicservice;
CREATE USER epicuser WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE epicservice TO epicuser;
\q

# 4. Міграції
alembic upgrade head

# 5. .env
cp .env.example .env
nano .env

# 6. systemd services
sudo cp deploy/epicservice.service /etc/systemd/system/
sudo cp deploy/webapp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable epicservice webapp
sudo systemctl start epicservice webapp

# 7. nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/epicservice
sudo ln -s /etc/nginx/sites-available/epicservice /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 8. SSL
sudo certbot --nginx -d your-domain.com
```

---

## 9. Моніторинг та логування

### 9.1 Логи

```bash
# Bot logs
journalctl -u epicservice -f
tail -f bot.log

# WebApp logs
journalctl -u webapp -f

# nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 9.2 Метрики

```bash
# Перевірка статусу
curl http://localhost:8000/health

# PostgreSQL connections
psql -U epicuser -d epicservice -c "SELECT count(*) FROM pg_stat_activity;"

# Redis info
redis-cli INFO
```

---

## 10. Безпека

### 10.1 Заходи

- ✅ HTTPS/TLS 1.3
- ✅ User ID валідація на кожному endpoint
- ✅ ADMIN_IDS whitelist
- ✅ SQL Injection захист (ORM)
- ✅ CORS налаштовано
- ✅ Rate limiting
- ✅ SSH keys only

### 10.2 Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 11. Продуктивність

### 11.1 Оптимізації

- **PostgreSQL:**
  - Connection pooling (asyncpg)
  - Indexes на `article`, `department`
  - `FOR UPDATE` locks для резервів

- **Redis:**
  - FSM storage
  - TTL для станів

- **PWA:**
  - Service Worker cache
  - Lazy loading
  - Debounce пошуку (500ms)

---

## 12. Troubleshooting

### 12.1 Bot не запускається

```bash
# Перевірити .env
cat .env

# Перевірити PostgreSQL
psql -U epicuser -d epicservice -c "\dt"

# Перевірити Redis
redis-cli PING
```

### 12.2 WebApp 404

```bash
# Перевірити nginx
sudo nginx -t
sudo systemctl status nginx

# Перевірити webapp service
sudo systemctl status webapp
```

### 12.3 Резерви не звільняються

```sql
-- Перевірити резерви
SELECT article, reserved FROM products WHERE reserved > 0;

-- Скинути резерви
UPDATE products SET reserved = 0;
```

---

## 📞 Підтримка

**Email:** [imerom25@gmail.com](mailto:imerom25@gmail.com)  
**Telegram:** @my_life_ukr  
**GitHub:** [github.com/imeromua/epicservice](https://github.com/imeromua/epicservice)

---

**Версія документа:** 2.0.0  
**Остання оновлення:** 19.02.2026
