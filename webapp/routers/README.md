# Webapp Routers

Цей каталог містить модульну структуру роутерів для FastAPI додатку.

## Структура

```
webapp/routers/
├── __init__.py          # Ініціалізація роутерів
├── client.py            # Клієнтські ендпоїнти
├── admin.py             # Адміністративні ендпоїнти
└── README.md            # Ця документація
```

## Клієнтський роутер (`client.py`)

**Префікс:** `/api`

### Ендпоїнти

#### Пошук та списки
- `POST /api/search` - Пошук товарів за артикулом/назвою
- `GET /api/list/{user_id}` - Отримати список користувача
- `GET /api/list/department/{user_id}` - Отримати відділ поточного списку

#### Управління списком
- `POST /api/add` - Додати товар до списку
- `POST /api/update` - Оновити кількість товару
- `POST /api/delete` - Видалити товар зі списку
- `POST /api/clear/{user_id}` - Очистити список
- `POST /api/save/{user_id}` - Зберегти список в Excel

#### Архіви
- `GET /api/archives/{user_id}` - Отримати список архівів
- `GET /api/statistics/{user_id}` - Статистика користувача
- `GET /api/archives/download-all/{user_id}` - Завантажити всі архіви (ZIP)
- `GET /api/archive/stats/{filename}` - Статистика архіву
- `GET /api/archive/download/{filename}` - Завантажити архівний файл
- `DELETE /api/archive/delete/{filename}` - Видалити архів

---

## Адміністративний роутер (`admin.py`)

**Префікс:** `/api/admin`  
**Авторизація:** Потрібні права адміністратора (`ADMIN_IDS`)

### Ендпоїнти

#### Управління користувачами
- `GET /api/admin/users` - Список всіх користувачів
- `GET /api/admin/users/active` - Користувачі з активними списками
- `POST /api/admin/force-save/{target_user_id}` - Примусове збереження списку користувача

#### Імпорт/Експорт
- `POST /api/admin/import` - Імпорт товарів з Excel, параметри: `file` (UploadFile), `user_id` (int), `notify_users` (bool, default False)
- `GET /api/admin/export/stock` - Експорт звіту по залишкам
- `GET /api/admin/export/collected` - Експорт зведеного звіту
- `POST /api/admin/subtract` - Віднімання зібраних товарів

#### Розсилка та статистика
- `POST /api/admin/broadcast` - Розіслати повідомлення всім користувачам
- `GET /api/admin/statistics` - Загальна статистика системи

### Авторизація

Всі адміністративні ендпоїнти захищені за допомогою `verify_admin` middleware:

```python
def verify_admin(user_id: int) -> int:
    """Перевіряє права адміністратора."""
    if user_id not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Access denied")
    return user_id
```

---

## Нотатки

- Нові адміністративні ендпоїнти доступні за префіксом `/api/admin/*`.
- Клієнтські ендпоїнти залишаються в `/api/*` (без зміни URL).

---

"Зроблено в Україні з ❤️"
