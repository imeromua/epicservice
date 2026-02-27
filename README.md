# 📦 EpicService

**Професійна система управління складськими замовленнями через Telegram Mini App**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://docs.aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io/)

---

## 🎯 Огляд проекту

EpicService — це комплексне рішення для управління замовленнями запчастин через Telegram, що складається з:

- **🤖 Telegram Bot** — мінімалістичний інтерфейс з persistent клавіатурою
- **🌐 Mini App (Telegram WebApp)** — повнофункціональний веб-додаток, який працює всередині Telegram
- **⚙️ Admin Panel** — потужна панель адміністратора з аналітикою
- **🗄️ Backend API** — FastAPI з асинхронною роботою з БД

---

## ✨ Основні можливості

### 👥 Для користувачів:
- 🔍 **Швидкий пошук** товарів за артикулом/назвою з debounce
- 📋 **Інтерактивні списки** з можливістю редагування кількості
- 🔒 **Блокування відділів** — один список = один відділ
- 📷 **Фотофіксація товарів** — завантаження до 3 фото, галерея в модальному вікні; фото стають видимими після модерації
- 📊 **Статистика** — персональна аналітика використання
- 📁 **Архів** — історія всіх збережених списків
- 📥 **ZIP експорт** — завантаження всіх архівів одним файлом
- 🔄 **Pull-to-refresh** — оновлення свайпом вниз
- 🌓 **Адаптивна тема** — автоматична темна/світла тема

### 👑 Для адміністраторів:
- 📊 **Аналітика** — детальна статистика користувачів, товарів, резервів
- 📥 **Імпорт** — завантаження товарів з Excel (drag & drop)
- 📤 **Експорт** — звіти про залишки
- 💾 **Примусове збереження** — завершення списків користувачів
- 📢 **Розсилка** — масові повідомлення всім користувачам
- 🗄️ **Управління архівами** — доступ до всіх файлів
- 🖼️ **Модерація фото** — схвалення/відхилення фото, черга `pending`, причина відхилення
- 🗑️ **Керування фото** — видалення фото (в т.ч. масові адмін-операції)
- 👥 **Управління користувачами** — RBAC: схвалення, блокування, ролі (pending → active → blocked)
- 📈 **Візуалізація** — графіки резервів по відділах

---

## 🏗️ Архітектура

```
epicservice/
├── bot.py                    # Telegram Bot (aiogram 3.x)
├── config.py                 # Конфігурація (.env)
├── database/
│   ├── models.py            # SQLAlchemy моделі
│   ├── engine.py            # Async engine
│   └── orm.py               # ORM queries
├── handlers/
│   ├── common.py            # /start, RBAC перевірка
│   ├── admin/               # Адмін-хендлери (bot)
│   │   ├── core.py
│   │   ├── import_handlers.py
│   │   ├── report_handlers.py
│   │   ├── archive_handlers.py
│   │   └── lock_common.py   # Блокування відділів
│   ├── webapp_handler.py    # Обробка webapp_data
│   └── error_handler.py     # Глобальна обробка помилок
├── webapp/
│   ├── api.py               # FastAPI додаток
│   ├── routers/
│   │   ├── client.py        # User API endpoints
│   │   ├── admin.py         # Admin API endpoints
│   │   ├── photos.py        # Photos API endpoints
│   │   └── user_management.py # RBAC / управління користувачами
│   ├── templates/
│   │   └── index.html       # Mini App frontend
│   ├── utils/
│   │   └── image_processing.py # Стиснення/обробка зображень
│   └── static/
│       ├── admin.html       # Статична адмін-сторінка (frontend)
│       ├── css/             # CSS файли (в т.ч. photos.css)
│       ├── js/              # JS файли (в т.ч. photos.js)
│       └── icons/           # Іконки
├── utils/
│   ├── list_processor.py    # Створення Excel
│   ├── archive_manager.py   # Ротація файлів
│   ├── force_save_helper.py # Примусове збереження
│   └── markdown_corrector.py # Корекція форматування
├── keyboards/
│   ├── inline.py            # Inline keyboards
│   └── webapp.py            # WebApp keyboards
├── middlewares/
│   └── logging_middleware.py
├── lexicon/
│   └── lexicon.py           # Текстові константи
└── archives/
    ├── active/              # Останні 10 файлів/user
    └── trash/               # Auto-cleanup через 14 днів
```

---

## 🚀 Технології

### Backend:
- **Python 3.11+** — сучасний асинхронний Python
- **aiogram 3.x** — Telegram Bot framework
- **FastAPI** — високопродуктивний веб-фреймворк
- **SQLAlchemy 2.0** — async ORM
- **PostgreSQL** — реляційна БД
- **Redis** — FSM storage та кешування
- **APScheduler** — фонові задачі (автоочищення)
- **openpyxl** — робота з Excel

### Frontend:
- **Vanilla JavaScript** — без фреймворків для максимальної швидкості
- **Telegram WebApp SDK** — нативна інтеграція
- **Adaptive CSS** — автотемування під Telegram

### DevOps:
- **systemd** — управління сервісами
- **nginx** — reverse proxy
- **Git** — version control

---

## 📋 Встановлення

### 🐳 Швидкий старт (Docker)

Найпростіший спосіб підняти проєкт локально — через Docker Compose:

```bash
cp .env.example .env
# заповни значення в .env
make up
```

Детальніше: [LOCAL_DEV.md](LOCAL_DEV.md)

---

### 1. Клонування репозиторію

```bash
git clone https://github.com/imeromua/epicservice.git
cd epicservice
```

### 2. Створення віртуального оточення

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Налаштування бази даних

```bash
# Створити БД PostgreSQL
sudo -u postgres psql
CREATE DATABASE epicservice;
CREATE USER epicuser WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE epicservice TO epicuser;
\q

# Виконати міграції
alembic upgrade head
```

### 4. Налаштування Redis

```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

### 5. Конфігурація .env

Створити файл `.env` в кореневій папці:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=123456789,987654321

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=epicservice
DB_USER=epicuser
DB_PASSWORD=your_password

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# WebApp
WEBAPP_URL=https://your-domain.com
WEBAPP_ADMIN_IDS=123456789,987654321
```

### 6. Запуск сервісів

#### Розробка (локально):

```bash
# Terminal 1: Bot
python bot.py

# Terminal 2: WebApp API
python webapp/api.py
```

#### Продакшн (systemd):

```bash
# Створити service файли
sudo nano /etc/systemd/system/epicservice.service
sudo nano /etc/systemd/system/webapp.service

# Запустити
sudo systemctl start epicservice webapp
sudo systemctl enable epicservice webapp

# Перевірити статус
sudo systemctl status epicservice
sudo systemctl status webapp
```

**Приклад service файлу** (`/etc/systemd/system/epicservice.service`):

```ini
[Unit]
Description=EpicService Telegram Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/epicservice
Environment="PATH=/home/your_user/epicservice/venv/bin"
ExecStart=/home/your_user/epicservice/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 🔧 Налаштування nginx

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📖 Документація API

Після запуску webapp API доступна автодокументація:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Основні ендпоінти:

#### **User API** (`/api`)
- `POST /api/search` - Пошук товарів
- `POST /api/products/filter` - Фільтрація товарів
- `GET /api/products/departments` - Список відділів
- `GET /api/list/{user_id}` - Поточний список
- `GET /api/list/department/{user_id}` - Поточний відділ списку
- `POST /api/add` - Додати товар
- `POST /api/update` - Оновити кількість
- `POST /api/delete` - Видалити товар
- `POST /api/save/{user_id}` - Зберегти список
- `POST /api/clear/{user_id}` - Очистити список
- `GET /api/archives/{user_id}` - Архіви користувача
- `GET /api/archives/download-all/{user_id}` - ZIP всіх архівів
- `GET /api/archive/stats/{filename}` - Статистика архіву
- `GET /api/archive/download/{filename}` - Завантажити архів
- `DELETE /api/archive/delete/{filename}` - Видалити архів
- `GET /api/statistics/{user_id}` - Статистика користувача

#### **Photos API** (`/api/photos`)
- `POST /api/photos/upload` - Завантажити фото (multipart: `photo`, `article`, `user_id`)
- `GET /api/photos/product/{article}` - Отримати approved фото товару
- `GET /api/photos/moderation/pending` - Черга фото на модерації (admin)
- `POST /api/photos/moderation/{photo_id}` - Схвалити/відхилити фото (admin)
- `DELETE /api/photos/{photo_id}` - Видалити фото (admin або автор)

#### **Admin API** (`/api/admin`)
- `GET /api/admin/statistics` - Загальна статистика
- `GET /api/admin/summary` - Зведена статистика
- `POST /api/admin/import` - Імпорт з Excel
- `GET /api/admin/export/stock` - Експорт залишків
- `POST /api/admin/force-save/{user_id}` - Примусове збереження
- `POST /api/admin/broadcast` - Розсилка повідомлень
- `GET /api/admin/users` - Список користувачів
- `GET /api/admin/users/all` - Всі користувачі (з статистикою)
- `GET /api/admin/users/active` - Активні списки
- `GET /api/admin/products/info` - Інфо про товари
- `GET /api/admin/reserved/by-department` - Резерви по відділах
- `GET /api/admin/archives` - Всі архіви
- `GET /api/admin/archives/download/{filename}` - Завантажити архів
- `GET /api/admin/archives/download-all` - ZIP всіх архівів

#### **User Management API** (`/api/admin/user-management`)
- `GET /api/admin/user-management/users` - Список користувачів (з RBAC)
- `POST /api/admin/user-management/approve` - Схвалити користувача
- `POST /api/admin/user-management/block` - Заблокувати користувача
- `POST /api/admin/user-management/unblock` - Розблокувати користувача
- `POST /api/admin/user-management/role` - Змінити роль користувача

---

## 🎨 Особливості UI/UX

### 🌈 Адаптивна тема
Автоматичне перемикання світлої/темної теми відповідно до налаштувань Telegram.

### 🔄 Pull-to-Refresh
Оновлення будь-якої вкладки свайпом вниз.

### ⚡ Haptic Feedback
Вібраційний відгук на дії користувача.

### 🧭 Запуск поза Telegram
Якщо Mini App відкрито у звичайному браузері, відображається підказка/оверлей з інструкцією перейти у Telegram, бо авторизація та робота додатку залежать від Telegram WebApp контексту.

---

## 🔒 Безпека

- ✅ Перевірка `user_id` на всіх ендпоінтах
- ✅ ADMIN_IDS для обмеження доступу до адмін-функцій
- ✅ Валідація вхідних даних (Pydantic)
- ✅ SQL injection захист (ORM)
- ✅ HTTPS only для production
- ✅ Безпечне зберігання паролів БД
- ✅ Фото: перевірка типу файлу (тільки `image/*`), ліміт кількості фото на товар, модерація перед публікацією

---

## 📊 Бізнес-логіка

### Резервування товарів
1. При додаванні товару в список → кількість резервується в БД
2. Товар стає недоступним для інших користувачів
3. При збереженні списку → резерв звільняється
4. При очищенні/видаленні → резерв також звільняється

### Блокування відділів
1. Перший товар у списку визначає відділ
2. Товари з інших відділів блокуються (grayscale + 🔒)
3. Після збереження/очищення блокування знімається

### Фото та модерація
1. Користувач завантажує фото → воно стискається і зберігається зі статусом `pending`
2. Адмін схвалює/відхиляє фото → тільки `approved` відображаються всім користувачам
3. Адмін може видалити фото (разом із файлом та записом у БД)

### Ротація файлів
1. **active/**: останні 10 файлів кожного користувача
2. **trash/**: старі файли (автоочищення через 14 днів)
3. Щоденна задача (APScheduler) о 03:00

---

## 🛠️ Maintenance

### Логи

```bash
# Bot logs
journalctl -u epicservice -f
tail -f bot.log

# WebApp logs
journalctl -u webapp -f
```

### Backup БД

```bash
pg_dump -U epicuser epicservice > backup_$(date +%Y%m%d).sql
```

### Очищення trash вручну

```bash
python -c "from utils.archive_manager import cleanup_trash; cleanup_trash(days=14)"
```

---

## 📈 Моніторинг

### Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"epicservice","version":"2.2.0"}
```

### Метрики

- Кількість активних користувачів
- Середня сума замовлення
- Популярні відділи
- Частота використання

---

## 🤝 Contribution

Проект розроблений для внутрішнього використання. Для пропозицій:

1. Fork репозиторій
2. Створіть feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit зміни (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Відкрийте Pull Request

---

## 📝 License

Внутрішній проект. Всі права захищено.

---

## 👨‍💻 Автор

**EpicService Team**
- GitHub: [@imeromua](https://github.com/imeromua)

---

## 🎯 Roadmap

- [ ] Експорт звітів у PDF
- [ ] Інтеграція з 1С
- [ ] Розширена аналітика (графіки, тренди)
- [ ] Багатомовність (англійська)

---

## 📞 Підтримка

Для питань та підтримки:
- 📧 Email: imerom25@gmail.com
- 💬 Telegram: @my_life_ukr

---

**Версія:** 2.3.0  
**Останнє оновлення:** 27.02.2026

"Зроблено в Україні з ❤️"
