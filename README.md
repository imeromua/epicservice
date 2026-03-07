# 📦 EpicService

**Внутрішня система управління складськими замовленнями через Telegram Bot + Telegram Mini App**

[![Version](https://img.shields.io/badge/version-3.0.1--beta-blue.svg)](https://github.com/imeromua/epicservice)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://docs.aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io/)

---

## Огляд

EpicService — це внутрішній сервіс для роботи із залишками, резервуванням товарів, списками замовлень, архівами та фотофіксацією товарів.

Система складається з:

- **Telegram Bot** — точка входу, авторизація через Telegram, службові повідомлення.
- **Telegram Mini App** — основний користувацький інтерфейс для пошуку, списків, фото та архівів.
- **Admin / Moderator tools** — імпорт, експорт, модерація фото, керування користувачами та сервісні операції.
- **FastAPI backend** — API, бізнес-логіка, робота з БД та файловим сховищем.

---

## Що нового в 3.0.1-beta

Реліз 3.0.1-beta акумулює виправлення та покращення після `v3.0.0`:

- ✅ Відфільтровано деактивовані товари з webapp endpoint'ів та операцій віднімання залишків.
- ✅ Виправлено баг із `onclick` JSON serialization, через який частина елементів списку могла бути неклікабельною.
- ✅ Додано адмінську операцію **«Відняти зібране»** через Excel.
- ✅ Виправлено file input flow для Telegram Mini App через `label`-обгортку.
- ✅ Додано вибір джерела фото: **Камера / Галерея**.
- ✅ Для камери реалізовано окремий flow через `getUserMedia()` з live preview, знімком, повтором та підтвердженням.
- ✅ Оновлено cache-bust для `photos.js` / `photos.css`, щоб Telegram Mini App не використовував застарілий кеш.

---

## Основні можливості

### Для користувачів
- 🔍 Пошук товарів за артикулом і назвою.
- 📋 Робота зі списком замовлення: додавання, редагування, видалення, збереження в Excel.
- 🔒 Блокування по відділу: в одному списку дозволено працювати тільки з одним відділом.
- 📁 Архіви збережених списків і ZIP-завантаження всіх архівів.
- 📊 Персональна статистика використання.
- 📷 Фото товарів: перегляд галереї, додавання фото, завантаження до модерації.
- 📲 У Telegram Mini App для фото доступні два сценарії: **галерея** або **камера**.
- 🎥 Для камери використовується прямий browser/WebApp flow через `getUserMedia()` без залежності від системного file picker.

### Для модераторів
- 🖼️ Окрема вкладка модерації фото.
- ✅ Схвалення або відхилення фото.
- 📝 Фіксація причини відхилення.
- 📥 Доступ до імпорту товарів та частини службових операцій згідно ролі.

### Для адміністраторів
- 📊 Загальна статистика по системі.
- 👥 Керування користувачами та ролями (`pending`, `active`, `blocked`, `moderator`, `admin`).
- 📥 Імпорт товарів з Excel.
- 📤 Експорт звітів про залишки.
- 📉 Операція **«Відняти зібране»** через Excel-файл.
- 💾 Примусове збереження активних списків.
- 📢 Масова розсилка повідомлень.
- 🗄️ Доступ до архівів та сервісних операцій.
- 🖼️ Повна модерація фото та адміністративне видалення фото.

---

## Архітектура

```text
epicservice/
├── bot.py                     # Telegram Bot (aiogram)
├── config.py                  # Конфігурація з .env
├── database/                  # SQLAlchemy models, engine, ORM
├── handlers/                  # Bot handlers, admin handlers, start/RBAC logic
├── webapp/
│   ├── api.py                 # FastAPI app
│   ├── routers/               # client/admin/photos/user_management endpoints
│   ├── templates/index.html   # Telegram Mini App shell
│   ├── static/js/             # frontend логіка Mini App
│   ├── static/css/            # стилі Mini App
│   └── utils/                 # image processing та helper-и
├── utils/                     # архіви, Excel, службова логіка
├── tests/                     # тести
├── LOCAL_DEV.md               # локальний запуск
├── TECHNICAL_GUIDE.md         # технічна документація
├── USER_GUIDE.md              # користувацька документація
├── PHOTO_FEATURE.md           # фотофункціонал
└── PRIVACY_POLICY.md          # політика конфіденційності
```

### Ключові технічні компоненти
- **Python 3.11+**
- **aiogram 3.x**
- **FastAPI**
- **SQLAlchemy 2.x (async)**
- **PostgreSQL**
- **Redis**
- **Vanilla JavaScript + Telegram WebApp SDK**
- **openpyxl** для Excel

---

## Бізнес-логіка

### Резервування товарів
1. Користувач додає товар у список.
2. Кількість резервується в БД.
3. Поки список активний, інші користувачі не можуть використати цей резерв.
4. Після збереження або очищення списку резерв звільняється.

### Блокування по відділу
1. Перший товар у списку визначає поточний відділ.
2. Товари з інших відділів у тому ж списку блокуються.
3. Після завершення списку блокування знімається.

### Фото товарів
1. Користувач натискає **«Додати фото»**.
2. У Telegram Mini App відкривається вибір **Камера / Галерея**.
3. Для **Галереї** використовується стандартний file input.
4. Для **Камери** відкривається camera-flow через `getUserMedia()` з live preview.
5. Після підтвердження фото стискається та завантажується на модерацію.
6. Іншим користувачам показуються тільки схвалені фото.

---

## API та ключові модулі

### User API
- `POST /api/search`
- `POST /api/products/filter`
- `GET /api/list/{user_id}`
- `POST /api/add`
- `POST /api/update`
- `POST /api/delete`
- `POST /api/save/{user_id}`
- `GET /api/archives/{user_id}`
- `GET /api/archives/download-all/{user_id}`
- `GET /api/statistics/{user_id}`

### Photos API
- `POST /api/photos/upload`
- `GET /api/photos/product/{article}`
- `GET /api/photos/moderation/pending`
- `POST /api/photos/moderation/{photo_id}`
- `DELETE /api/photos/{photo_id}`

### Admin API
- `GET /api/admin/statistics`
- `POST /api/admin/import`
- `GET /api/admin/export/stock`
- `POST /api/admin/force-save/{user_id}`
- `POST /api/admin/broadcast`
- `GET /api/admin/users`
- `GET /api/admin/archives`
- `POST /api/admin/subtract-collected` *(якщо ввімкнено у поточній реалізації API)*

### User Management API
- `GET /api/admin/user-management/users`
- `POST /api/admin/user-management/approve`
- `POST /api/admin/user-management/block`
- `POST /api/admin/user-management/unblock`
- `POST /api/admin/user-management/role`

Після запуску FastAPI автодокументація доступна у Swagger / ReDoc:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

---

## Швидкий старт

### Docker / локальний dev

```bash
cp .env.example .env
make up
```

Деталі локального запуску: [LOCAL_DEV.md](LOCAL_DEV.md)

### Ручний запуск

```bash
git clone https://github.com/imeromua/epicservice.git
cd epicservice
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

Запуск сервісів:

```bash
python bot.py
python webapp/api.py
```

---

## Мінімальні змінні середовища

Приклад дивись у `.env.example`.

```env
BOT_TOKEN=...
ADMIN_IDS=123456789
WEBAPP_URL=https://your-domain.com
WEBAPP_ADMIN_IDS=123456789

DB_HOST=localhost
DB_PORT=5432
DB_NAME=epicservice
DB_USER=epicuser
DB_PASSWORD=...

REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

---

## UI / UX особливості

- Telegram-native поведінка у Mini App.
- Підтримка тем Telegram.
- Pull-to-refresh.
- Haptic feedback.
- Захист від запуску поза Telegram: якщо Mini App відкрито в звичайному браузері, користувач бачить екран-підказку з переходом у Telegram.
- Для фото використовується окремий camera modal з live preview, повторним знімком і підтвердженням відправки.

---

## Безпека

- Авторизація ґрунтується на Telegram WebApp / Telegram user context.
- Доступ до адмінських і модераторських функцій обмежено ролями.
- На API використовується валідація даних і перевірка `user_id`.
- У production рекомендовано використовувати тільки HTTPS.
- Фото проходять модерацію перед тим, як стати видимими всім користувачам.

---

## Документація

- [LOCAL_DEV.md](LOCAL_DEV.md)
- [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)
- [USER_GUIDE.md](USER_GUIDE.md)
- [PHOTO_FEATURE.md](PHOTO_FEATURE.md)
- [PRIVACY_POLICY.md](PRIVACY_POLICY.md)
- [ANDROID_APP.md](ANDROID_APP.md)

---

## Підтримка

- Email: [imerom25@gmail.com](mailto:imerom25@gmail.com)
- Telegram: [@my_life_ukr](https://t.me/my_life_ukr)
- GitHub: [github.com/imeromua/epicservice](https://github.com/imeromua/epicservice)

---

## Поточна версія

**Версія:** `3.0.1-beta`  
**Останнє оновлення README:** `07.03.2026`

---

Зроблено в Україні з ❤️
