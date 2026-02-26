# 🛠️ Технічний посібник EpicService

**Версія:** 2.2.0  
**Останнє оновлення:** 25.02.2026

Цей документ надає поглиблений технічний огляд EpicService, призначений для розробників, DevOps-інженерів та системних адміністраторів.

---

## 📚 Зміст

1. [Архітектура системи](#1-архітектура-системи)
2. [Технологічний стек](#2-технологічний-стек)
3. [Схема бази даних](#3-схема-бази-даних)
4. [Backend (Telegram Bot)](#4-backend-telegram-bot)
5. [WebApp (Mini App)](#5-webapp-mini-app)
6. [Адмін-панель](#6-адмін-панель)
7. [Ключові бізнес-процеси](#7-ключові-бізнес-процеси)
8. [API документація](#8-api-документація)
9. [Розгортання](#9-розгортання)
10. [Моніторинг та логування](#10-моніторинг-та-логування)
11. [Безпека](#11-безпека)
12. [Продуктивність](#12-продуктивність)
13. [Troubleshooting](#13-troubleshooting)

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
┌───┴────┐ ┌─┴──────────────────┐
│ Bot API │ │ WebApp (Mini App) │
│ aiogram │ │ FastAPI + HTML    │
└───┬────┘ └─┬──────────────────┘
    │         │
    └─────────┤
              │
┌─────────────┴───────────┐
│ PostgreSQL (Основні дані)│
└─────────┬───────────────┘
          │
     ┌────┼────┐
     │ Redis    │
     │ (FSM)    │
     └─────────┘
```

### 1.2 Потік даних

1. **Користувач → Telegram Bot:**
   - Команди `/start`, `/admin`
   - Persistent клавіатура (кнопка "Адмінка")
   - Callback queries (інлайн кнопки)

2. **Користувач → WebApp:**
   - Відкривається через `web_app` кнопку в боті
   - Додаток працює у Telegram WebApp контексті (для авторизації та доступу до `initData`)
   - REST API запити до FastAPI

3. **Bot/WebApp → PostgreSQL:**
   - Async ORM (SQLAlchemy 2.0)
   - Записи транзакцій
   - `FOR UPDATE` locks для резервів

4. **Bot → Redis:**
   - FSM states (стани користувачів)
   - Тимчасовий кеш

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
| **Стилі** | CSS Variables (темування) |
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
┌────────────────────────────┐
│          User               │
├────────────────────────────┤
│ id (PK, BigInt)            │
│ username                   │
│ first_name                 │
│ created_at                 │
│ status (pending/active/    │
│         blocked)           │
│ role (user/admin)          │
│ approved_by                │
│ approved_at                │
│ blocked_by                 │
│ blocked_at                 │
│ blocked_reason             │
│ updated_at                 │
└─────┬──────────────────────┘
     │
     │ 1:N
     │
┌────┼────────────────┐
│    TempList          │
├────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ product_id (FK) ───┬───────────────────────┐
│ quantity            │ ┌───────────────────────────┤
│                     │ │       Product              │
└────────────────────┘ ├───────────────────────────┤
                         │ id (PK)                    │
┌────────────────────┐ │ артикул (UNIQUE, INDEX)    │
│    SavedList        │ │ назва                      │
├────────────────────┤ │ відділ                     │
│ id (PK)            │ │ група                      │
│ user_id (FK)       │ │ кількість                  │
│ file_name          │ │ відкладено (резерв)       │
│ file_path          │ │ місяці_без_руху            │
│ created_at         │ │ сума_залишку               │
└───┬─────────────────┘ │ ціна                       │
   │                    │ активний                   │
   │ 1:N                └──────────┬────────────────┘
   │                               │ 1:N
┌──┼────────────────────┐ ┌──────┼────────────────────┐
│  SavedListItem       │ │  ProductPhoto              │
├──────────────────────┤ ├──────────────────────────┤
│ id (PK)             │ │ id (PK)                    │
│ list_id (FK)        │ │ артикул (FK)               │
│ article_name        │ │ file_path                  │
│ quantity            │ │ file_size                  │
└──────────────────────┘ │ original_size              │
                          │ photo_order                │
                          │ uploaded_by (FK → User)    │
                          │ uploaded_at                │
                          │ status (pending/approved/  │
                          │         rejected)          │
                          │ moderated_by (FK → User)   │
                          │ moderated_at               │
                          │ rejection_reason           │
                          └────────────────────────────┘
```

### 3.2 Основні таблиці

#### **User**
Зберігає інформацію про користувачів Telegram.
- `id` — Telegram User ID (Primary Key, BigInteger)
- `username`, `first_name` — з Telegram
- `created_at` — дата першого входу
- `status` — стан доступу: `pending` (очікує), `active` (активний), `blocked` (заблокований)
- `role` — роль: `user` (звичайний), `admin` (адміністратор)
- `approved_by`, `approved_at` — хто та коли схвалив
- `blocked_by`, `blocked_at`, `blocked_reason` — хто, коли та чому заблокував
- `updated_at` — дата останнього оновлення запису

#### **Product**
Каталог товарів (назви колонок — кирилиця, відповідає структурі БД).
- `id` — внутрішній ID
- `артикул` — унікальний артикул (UNIQUE INDEX)
- `назва`, `відділ`, `група` — описові поля
- `кількість` — доступна кількість (String для гнучкості)
- `відкладено` — зарезервована кількість
- `місяці_без_руху` — місяців без руху (діагностика)
- `сума_залишку` — сума залишку
- `ціна` — ціна за одиницю
- `активний` — м'яке видалення

#### **ProductPhoto**
Фото товарів з модерацією.
- `артикул` — FK на Product
- `file_path` — шлях на сервері
- `file_size`, `original_size` — розмір після стискання та оригінальний
- `photo_order` — порядок (0, 1, 2)
- `uploaded_by`, `uploaded_at` — автор та дата
- `status` — `pending`, `approved`, `rejected`
- `moderated_by`, `moderated_at`, `rejection_reason` — дані модерації

#### **TempList**
Поточні (незбережені) списки користувачів.
- `user_id` + `product_id` — зовнішні ключі
- `quantity` — кількість у списку

**Логіка:** При додаванні товару в список → `product.відкладено += quantity`

#### **SavedList / SavedListItem**
Збережені списки та їхні позиції.
- Зберігаються після натискання "💾 Зберегти"
- `file_name` / `file_path` — Excel файл у `archives/active/`
- `SavedListItem` — позиції: `article_name`, `quantity`

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
  common.py              # /start, RBAC перевірка, персистент клавіатура
  archive.py             # Архівні операції
  user_search.py         # Пошук (deprecated, логіка в webapp)
  webapp_handler.py      # Обробка webapp_data
  error_handler.py       # Глобальні помилки
  admin/
    core.py              # Основні адмін-команди
    import_handlers.py   # Імпорт Excel
    report_handlers.py   # Звіти
    archive_handlers.py  # Архіви
    lock_common.py       # Блокування відділів
  user/                  # Deprecated (логіка перенесена в webapp)
    list_editing.py
    list_management.py
    list_saving.py

keyboards/
  inline.py              # Inline keyboards
  webapp.py              # WebApp keyboards

middlewares/
  logging_middleware.py  # Логування

utils/
  list_processor.py      # Створення Excel
  archive_manager.py     # Ротація файлів
  card_generator.py      # Генерація карток
  force_save_helper.py   # Примусове збереження
  markdown_corrector.py  # Корекція форматування

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

## 5. WebApp (Mini App)

### 5.1 Архітектура

```
webapp/
  api.py                 # FastAPI додаток
  routers/
    client.py            # User endpoints
    admin.py             # Admin endpoints
    photos.py            # Photos endpoints
    user_management.py   # RBAC / управління користувачами
  templates/
    index.html           # SPA frontend
  utils/
    image_processing.py  # Стиснення/обробка зображень
  static/
    admin.html           # Адмін-сторінка
    css/                 # Статичні стилі
    js/                  # Статичні скрипти
    icons/               # Іконки
```

### 5.2 Запуск поза Telegram

Mini App залежить від Telegram WebApp контексту (`window.Telegram.WebApp`, `initData`). При відкритті у звичайному браузері відображається підказка/оверлей перейти до Telegram.

### 5.3 API Endpoints

#### **Client API** (`/api/*`)

| Method | Endpoint | Опис |
|--------|----------|------|
| POST | `/api/search` | Пошук товарів |
| POST | `/api/products/filter` | Фільтрація товарів |
| GET | `/api/products/departments` | Список відділів |
| GET | `/api/list/{user_id}` | Поточний список |
| GET | `/api/list/department/{user_id}` | Поточний відділ |
| POST | `/api/add` | Додати товар |
| POST | `/api/update` | Оновити кількість |
| POST | `/api/delete` | Видалити товар |
| POST | `/api/save/{user_id}` | Зберегти список |
| POST | `/api/clear/{user_id}` | Очистити список |
| GET | `/api/archives/{user_id}` | Архіви |
| GET | `/api/archive/download/{filename}` | Завантажити файл |
| DELETE | `/api/archive/delete/{filename}` | Видалити архів |
| GET | `/api/archives/download-all/{user_id}` | ZIP експорт |
| GET | `/api/statistics/{user_id}` | Статистика користувача |
| GET | `/api/archive/stats/{filename}` | Статистика архіву |

#### **Photos API** (`/api/photos/*`)

| Method | Endpoint | Опис |
|--------|----------|------|
| POST | `/api/photos/upload` | Завантажити фото (multipart) |
| GET | `/api/photos/product/{article}` | Approved фото товару |
| GET | `/api/photos/moderation/pending` | Черга на модерацію (admin) |
| POST | `/api/photos/moderation/{photo_id}` | Схвалити/відхилити (admin) |
| DELETE | `/api/photos/{photo_id}` | Видалити фото |

#### **Admin API** (`/api/admin/*`)

| Method | Endpoint | Опис |
|--------|----------|------|
| GET | `/api/admin/statistics` | Загальна статистика |
| GET | `/api/admin/summary` | Зведена статистика |
| POST | `/api/admin/import` | Імпорт Excel |
| GET | `/api/admin/export/stock` | Експорт залишків |
| POST | `/api/admin/force-save/{target_user_id}` | Примусове збереження |
| POST | `/api/admin/broadcast` | Розсилка повідомлень |
| GET | `/api/admin/users` | Список користувачів |
| GET | `/api/admin/users/all` | Всі користувачі (з статистикою) |
| GET | `/api/admin/users/active` | Активні списки |
| GET | `/api/admin/products/info` | Інфо про товари |
| GET | `/api/admin/reserved/by-department` | Резерви по відділах |
| GET | `/api/admin/archives` | Всі архіви всіх юзерів |
| GET | `/api/admin/archives/download/{filename}` | Завантажити архів |
| GET | `/api/admin/archives/download-all` | ZIP всіх архівів |

#### **User Management API** (`/api/admin/user-management/*`)

| Method | Endpoint | Опис |
|--------|----------|------|
| GET | `/api/admin/user-management/users` | Список користувачів (RBAC) |
| POST | `/api/admin/user-management/approve` | Схвалити користувача |
| POST | `/api/admin/user-management/block` | Заблокувати |
| POST | `/api/admin/user-management/unblock` | Розблокувати |
| POST | `/api/admin/user-management/role` | Змінити роль |

---

## 6. Адмін-панель

### 6.1 Функціонал

#### **6.1.1 Статистика**

**Кліка більні картки:**
```javascript
// Картка "Всі користувачі"
<div class="admin-stat-card" onclick="showAllUsers()">
  <div class="admin-stat-icon">👥</div>
  <div class="admin-stat-value">${data.total_users}</div>
  <div class="admin-stat-label">Користувачів</div>
</div>

// При кліку → модальне вікно зі списком
function showAllUsers() {
  fetch('/api/admin/users/all?user_id=' + userId)
    .then(r => r.json())
    .then(data => renderUsersModal(data));
}
```

**Доступні картки:**
1. 👥 **Всі користувачі** → список з ID, ім'ям, датою реєстрації
2. 🔥 **Активні списки** → користувачі з незбереженими списками + примусове збереження
3. 📦 **Товари** → статистика по відділах, групах
4. 💰 **Резерви** → зарезервовані суми по відділах (з графіками)

#### **6.1.2 Імпорт Excel**

**Drag & Drop інтерфейс:**
```javascript
const dropZone = document.getElementById('dropZone');

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  const files = e.dataTransfer.files;
  if (files.length > 0 && files[0].name.match(/\.(xlsx|xls)$/)) {
    selectedFile = files[0];
    document.getElementById('uploadBtn').disabled = false;
  }
});

async function uploadFile() {
  const formData = new FormData();
  formData.append('file', selectedFile);
  
  const notifyUsers = document.getElementById('notifyUsers').checked;
  
  const response = await fetch(
    `/api/admin/import?user_id=${userId}&notify_users=${notifyUsers}`,
    { method: 'POST', body: formData }
  );
  
  const result = await response.json();
  // Показує: додано X, оновлено Y, деактивовано Z
}
```

**Формат Excel:**
- **Стовпці:** Артикул, Назва, Відділ, Група, Ціна, Доступно, Без руху
- **Синоніми підтримуються** (config: `column_synonyms.json`)

**Процес імпорту:**
1. Перевірка формату файлу
2. Парсинг Excel → список товарів
3. Порівняння з БД:
   - Нові → INSERT
   - Існуючі → UPDATE
   - Відсутні в файлі → `is_active = False`
4. Опціонально: розсилка повідомлень користувачам

#### **6.1.3 Примусове збереження**

```python
@router.post("/api/admin/force-save/{target_user_id}")
async def admin_force_save(
    target_user_id: int,
    user_id: int = Query(...)
):
    # Перевірка адміна
    if user_id not in ADMIN_IDS:
        raise HTTPException(403, "Forbidden")
    
    # Зберігаємо список target_user_id
    await process_and_save_list(target_user_id)
    
    # Відправляємо повідомлення через бота
    await bot.send_message(
        target_user_id,
        "✅ Ваш список було автоматично збережено адміністратором."
    )
    
    return {"success": True, "message": "Список збережено"}
```

**UI:**
- Відображається в модальному вікні "Активні списки"
- Кнопка 💾 біля кожного користувача

#### **6.1.4 Розсилка повідомлень**

```javascript
async function sendBroadcast() {
  const message = document.getElementById('broadcastMessage').value.trim();
  
  if (!message) {
    alert('⚠️ Введіть повідомлення');
    return;
  }
  
  const response = await fetch(
    `/api/admin/broadcast?user_id=${userId}`,
    {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ user_id: userId, message: message })
    }
  );
  
  const result = await response.json();
  alert(`✅ Розіслано ${result.sent} користувачам`);
}
```

**Backend:**
```python
@router.post("/api/admin/broadcast")
async def admin_broadcast(
    request: BroadcastRequest,
    user_id: int = Query(...)
):
    if user_id not in ADMIN_IDS:
        raise HTTPException(403)
    
    users = await get_all_users()
    sent_count = 0
    
    for user in users:
        try:
            await bot.send_message(user.id, request.message)
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user.id}: {e}")
    
    return {"success": True, "sent": sent_count}
```

#### **6.1.5 Експорт звітів**

**Звіт про залишки (Excel):**
```python
@router.get("/api/admin/export/stock")
async def export_stock(user_id: int = Query(...)):
    if user_id not in ADMIN_IDS:
        raise HTTPException(403)
    
    products = await get_all_active_products()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Залишки"
    
    # Заголовки
    ws.append(["Артикул", "Назва", "Відділ", "Доступно", "Зарезервовано", "Ціна"])
    
    # Дані
    for p in products:
        ws.append([p.article, p.name, p.department, p.available, p.reserved, p.price])
    
    # Зберігаємо
    filename = f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = f"archives/reports/{filename}"
    wb.save(filepath)
    
    return FileResponse(filepath, filename=filename)
```

**ZIP всіх архівів:**
```python
@router.get("/api/admin/archives/download-all")
async def download_all_archives(user_id: int = Query(...)):
    if user_id not in ADMIN_IDS:
        raise HTTPException(403)
    
    zip_filename = f"all_archives_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = f"archives/temp/{zip_filename}"
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for user_folder in Path("archives/active").iterdir():
            for file in user_folder.glob("*.xlsx"):
                zipf.write(file, arcname=f"{user_folder.name}/{file.name}")
    
    return FileResponse(zip_path, filename=zip_filename)
```

---

## 7. Ключові бізнес-процеси

### 7.1 Резервування товарів

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

### 7.2 Блокування відділів

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

### 7.3 Збереження списку

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

### 7.4 Ротація файлів

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

## 8. API документація

### 8.1 Swagger UI

Автогенерована документація:
- http://localhost:8000/docs
- http://localhost:8000/redoc

### 8.2 Приклад запиту

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

## 9. Розгортання

### 9.1 Вимоги

- Ubuntu 22.04 LTS
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- nginx
- SSL certificate (Let's Encrypt)

### 9.2 Покрокова інструкція

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

## 10. Моніторинг та логування

### 10.1 Логи

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

### 10.2 Метрики

```bash
# Перевірка статусу
curl http://localhost:8000/health

# PostgreSQL connections
psql -U epicuser -d epicservice -c "SELECT count(*) FROM pg_stat_activity;"

# Redis info
redis-cli INFO

# Дисковий простір архівів
du -sh archives/active/
du -sh archives/trash/
```

---

## 11. Безпека

### 11.1 Заходи

- ✅ HTTPS/TLS 1.3
- ✅ User ID валідація на кожному endpoint
- ✅ ADMIN_IDS whitelist
- ✅ SQL Injection захист (ORM)
- ✅ CORS налаштовано
- ✅ Rate limiting
- ✅ SSH keys only

### 11.2 Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 11.3 Регулярні оновлення

```bash
# Оновлення системи
sudo apt update && sudo apt upgrade -y

# Оновлення Python залежностей
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

---

## 12. Продуктивність

### 12.1 Оптимізації

- **PostgreSQL:**
  - Connection pooling (asyncpg)
  - Indexes на `article`, `department`
  - `FOR UPDATE` locks для резервів

- **Redis:**
  - FSM storage
  - TTL для станів

- **WebApp:**
  - Lazy loading
  - Debounce пошуку (500ms)

### 12.2 Benchmark

```bash
# API endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# PostgreSQL
pgbench -i -s 50 epicservice
pgbench -c 10 -j 2 -t 1000 epicservice
```

---

## 13. Troubleshooting

### 13.1 Bot не запускається

```bash
# Перевірити .env
cat .env

# Перевірити PostgreSQL
psql -U epicuser -d epicservice -c "\dt"

# Перевірити Redis
redis-cli PING

# Логи
journalctl -u epicservice -n 50
```

### 13.2 WebApp 404

```bash
# Перевірити nginx
sudo nginx -t
sudo systemctl status nginx

# Перевірити webapp service
sudo systemctl status webapp

# Логи nginx
tail -f /var/log/nginx/error.log
```

### 13.3 Резерви не звільняються

```sql
-- Перевірити резерви
SELECT article, reserved FROM products WHERE reserved > 0;

-- Скинути резерви (ОБЕРЕЖНО!)
UPDATE products SET reserved = 0;

-- Перевірити TempList
SELECT user_id, COUNT(*) FROM temp_list GROUP BY user_id;
```

### 13.4 Mini App відкривається в браузері

Якщо додаток відкрито поза Telegram:

1. Відкрийте його через кнопку **"🌐 Відкрити додаток"** у боті.
2. Перевірте, що `WEBAPP_URL` в `.env` вказує на правильний домен.
3. Переконайтеся, що сторінка не кешується сторонніми проксі/CDN агресивно.

---

## 📞 Підтримка

**Email:** [imerom25@gmail.com](mailto:imerom25@gmail.com)  
**Telegram:** [@my_life_ukr](https://t.me/my_life_ukr)  
**GitHub:** [github.com/imeromua/epicservice](https://github.com/imeromua/epicservice)

---

**Версія документа:** 2.2.0  
**Останнє оновлення:** 25.02.2026

"Зроблено в Україні з ❤️"
