# Webapp Routers

Цей каталог містить модульну структуру роутерів для FastAPI додатку.

## Структура

```
webapp/routers/
├── __init__.py              # Ініціалізація роутерів
├── client.py                # Клієнтські ендпоїнти
├── admin.py                 # Адміністративні ендпоїнти
├── photos.py                # Ендпоїнти фото товарів
├── user_management.py       # RBAC / управління користувачами
└── README.md                # Ця документація
```

## Клієнтський роутер (`client.py`)

**Префікс:** `/api`

### Ендпоїнти

#### Пошук та списки
- `POST /api/search` - Пошук товарів за артикулом/назвою
- `POST /api/products/filter` - Фільтрація товарів
- `GET /api/products/departments` - Список відділів
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
- `GET /api/admin/users/all` - Всі користувачі (з статистикою)
- `GET /api/admin/users/active` - Користувачі з активними списками
- `POST /api/admin/force-save/{target_user_id}` - Примусове збереження списку користувача

#### Імпорт/Експорт
- `POST /api/admin/import` - Імпорт товарів з Excel, параметри: `file` (UploadFile), `user_id` (int), `notify_users` (bool, default False)
- `GET /api/admin/export/stock` - Експорт звіту по залишкам

#### Архіви
- `GET /api/admin/archives` - Список всіх архівів
- `GET /api/admin/archives/download/{filename}` - Завантажити архів
- `GET /api/admin/archives/download-all` - ZIP всіх архівів

#### Розсилка та статистика
- `POST /api/admin/broadcast` - Розіслати повідомлення всім користувачам
- `GET /api/admin/statistics` - Загальна статистика системи
- `GET /api/admin/summary` - Зведена статистика
- `GET /api/admin/products/info` - Інформація про товари
- `GET /api/admin/reserved/by-department` - Резерви по відділах

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

## Роутер фото (`photos.py`)

**Префікс:** `/api/photos`

### Ендпоїнти

- `POST /api/photos/upload` - Завантажити фото (multipart: `photo`, `article`, `user_id`; макс. 3 фото на товар)
- `GET /api/photos/product/{article}` - Отримати approved фото товару
- `GET /api/photos/moderation/pending` - Черга фото на модерацію (admin)
- `POST /api/photos/moderation/{photo_id}` - Схвалити/відхилити фото (admin): `status`, `reason`, `user_id`
- `DELETE /api/photos/{photo_id}` - Видалити фото (admin або автор)

---

## Роутер управління користувачами (`user_management.py`)

**Префікс:** `/api/admin/user-management`  
**Авторизація:** Потрібні права адміністратора

### Ендпоїнти

- `GET /api/admin/user-management/users` - Список користувачів з RBAC-статусами
- `POST /api/admin/user-management/approve` - Схвалити користувача (pending → active)
- `POST /api/admin/user-management/block` - Заблокувати користувача
- `POST /api/admin/user-management/unblock` - Розблокувати користувача
- `POST /api/admin/user-management/role` - Змінити роль користувача

---

## Нотатки

- Нові адміністративні ендпоїнти доступні за префіксом `/api/admin/*`.
- Клієнтські ендпоїнти залишаються в `/api/*` (без зміни URL).

---

"Зроблено в Україні з ❤️"
