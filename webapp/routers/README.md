# Webapp Routers

Цей каталог містить модульну структуру роутерів для FastAPI додатку.

## Структура

```
webapp/routers/
├── __init__.py          # Ініціалізація роутерів
├── client.py           # Клієнтські ендпоїнти
├── admin.py            # Адміністративні ендпоїнти
└── README.md           # Ця документація
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

### Приклад використання

```javascript
// Пошук товарів
fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        query: 'артикул або назва',
        user_id: 12345
    })
});

// Додати товар
fetch('/api/add', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        user_id: 12345,
        product_id: 1,
        quantity: 5
    })
});
```

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
- `POST /api/admin/import` - Імпорт товарів з Excel
  - **Параметри:**
    - `file`: UploadFile - Excel файл
    - `user_id`: int - ID адміністратора
    - `notify_users`: bool - Розіслати сповіщення (default: False)
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

### Приклад використання

```javascript
// Імпорт товарів
const formData = new FormData();
formData.append('file', excelFile);
formData.append('user_id', adminId);
formData.append('notify_users', true);

fetch('/api/admin/import', {
    method: 'POST',
    body: formData
});

// Отримати статистику
fetch('/api/admin/statistics?user_id=' + adminId);

// Розсилка повідомлення
fetch('/api/admin/broadcast', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        user_id: adminId,
        message: 'Важливе оголошення'
    })
});
```

---

## Переваги модульної структури

1. **Розділення відповідальності** - клієнтська та адміністративна логіка розділена
2. **Легке тестування** - можна тестувати кожен роутер окремо
3. **Масштабованість** - легко додавати нові ендпоїнти без перевантаження основного файлу
4. **Безпека** - адміністративна логіка ізольована з перевіркою прав
5. **Підтримка** - простіше розуміти та модифікувати код

---

## Розробка

### Додавання нового ендпоїнту

1. Визначте, чи це клієнтський чи адміністративний ендпоїнт
2. Додайте функцію в відповідний роутер
3. Використовуйте декоратор `@router.get/post/put/delete`
4. Для адмінки додайте `user_id: int = Depends(verify_admin)`

### Приклад

```python
# У client.py
@router.get("/new-endpoint/{user_id}")
async def new_client_endpoint(user_id: int):
    return {"message": "Client endpoint"}

# У admin.py
@router.post("/new-admin-endpoint")
async def new_admin_endpoint(user_id: int = Depends(verify_admin)):
    return {"message": "Admin endpoint"}
```

---

## Міграція з монолітного `api.py`

Всі ендпоїнти з оригінального `api.py` перенесені в `client.py`. Старі URL залишаються робочими:

- `/api/search` → `/api/search` (без змін)
- `/api/list/{user_id}` → `/api/list/{user_id}` (без змін)
- тощо...

Нові адміністративні ендпоїнти доступні за префіксом `/api/admin/*`.
