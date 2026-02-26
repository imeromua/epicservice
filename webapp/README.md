# 🌐 EpicService WebApp (Frontend)

**Повнофункціональний Telegram Mini App**

---

## 📚 Зміст

- [Огляд](#огляд)
- [Архітектура](#архітектура)
- [Технології](#технології)
- [Основні компоненти](#основні-компоненти)
- [API інтеграція](#api-інтеграція)
- [Адмін-панель](#адмін-панель)
- [UI/UX особливості](#uiux-особливості)
- [Запуск](#запуск)

---

## 🎯 Огляд

WebApp — це клієнтська частина проекту EpicService, яка виконується як Telegram Mini App.

### Основні можливості:

#### 👥 Користувачі:
- 🔍 **Пошук** товарів з debounce (500ms)
- 📋 **Списки** з редагуванням та видаленням
- 🔒 **Блокування відділів** — візуальна індикація
- 📷 **Фото товарів** — завантаження, галерея, модерація
- 📊 **Статистика** — красива картка з градієнтом
- 📁 **Архів** — з детальною інформацією
- 📥 **ZIP експорт** всіх архівів
- 🔄 **Pull-to-refresh** на всіх вкладках
- 🌓 **Адаптивна тема** (dark/light)

#### 👑 Адміністратори:
- 📊 **Аналітика** з клікабельними картками
- 📥 **Імпорт** Excel з drag & drop
- 📤 **Експорт** звітів
- 💾 **Примусове збереження** списків
- 📢 **Розсилка** повідомлень
- 📈 **Візуалізація** резервів по відділах
- 🖼️ **Модерація фото** — черга pending, схвалення/відхилення
- 👥 **Управління користувачами** — RBAC (approve/block/unblock/role)

---

## 🏗️ Архітектура

```
webapp/
├── api.py                  # FastAPI додаток
├── routers/
│   ├── client.py          # User API endpoints
│   ├── admin.py           # Admin API endpoints
│   ├── photos.py          # Photos API endpoints
│   └── user_management.py # RBAC / управління користувачами
├── templates/
│   └── index.html         # Основний SPA
├── utils/
│   └── image_processing.py # Стиснення/обробка зображень
└── static/
    ├── admin.html         # Адмін-панель (статична)
    ├── css/               # Стилі (variables, layout, photos, admin, ...)
    ├── js/                # Скрипти (app, search, list, photos, admin, ...)
    └── icons/
        ├── icon-192x192.png
        ├── icon-512x512.png
        └── ...
```

---

## 🚀 Технології

### Frontend:
- **Vanilla JavaScript** — без фреймворків для максимальної швидкості
- **Telegram WebApp SDK** — `window.Telegram.WebApp`
- **CSS Variables** — динамічне темування

### Backend (API):
- **FastAPI** — async Python web framework
- **Jinja2** — template engine
- **asyncpg** — async PostgreSQL driver

---

## 🧩 Основні компоненти

### 1. **Пошук** (🔍 Search Tab)

```javascript
// Debounce пошуку (500ms)
document.getElementById('searchInput').addEventListener('input', (e) => {
  clearTimeout(searchTimeout);
  const query = e.target.value.trim();
  
  if (query.length < 2) {
    document.getElementById('searchResults').innerHTML = '';
    return;
  }
  
  searchTimeout = setTimeout(() => search(query), 500);
});

// Рендер товару з блокуванням
function renderProduct(p) {
  const isLocked = p.is_different_department;
  const lockedClass = isLocked ? ' locked' : '';
  
  return `<div class="product-card${lockedClass}">
    <div class="lock-overlay">🔒</div>
    <!-- ... -->
  </div>`;
}
```

**Особливості:**
- Візуальне блокування (grayscale + 🔒)
- Індикація доступності/резерву
- Детальна інфо (відділ, група, без руху, ціна)

### 2. **Список** (📋 List Tab)

```javascript
async function loadList() {
  const response = await fetch(`/api/list/${userId}`);
  const data = await response.json();
  
  // Оновлюємо інфо про відділ
  const deptResponse = await fetch(`/api/list/department/${userId}`);
  const deptData = await deptResponse.json();
  updateDepartmentInfo(deptData.department, data.count);
  
  // Показуємо Total Box
  document.getElementById('totalSum').textContent = data.total.toFixed(2);
  document.getElementById('totalBox').style.display = 'flex';
}
```

**Особливості:**
- Sticky Total Box знизу
- Інфо про поточний відділ
- Редагування кількості через модальне вікно

### 3. **Архів** (📁 Archives Tab)

```javascript
async function loadArchives() {
  // Статистика користувача
  const stats = await loadStatistics();
  if (stats) statsCard.innerHTML = stats;
  
  // Список архівів
  const response = await fetch(`/api/archives/${userId}`);
  const data = await response.json();
  
  // Кнопка ZIP експорту
  html += `<button class="download-all-btn" 
            onclick="downloadAllArchives()">
    📦 Завантажити всі архіви (${data.archives.length})
  </button>`;
}
```

**Особливості:**
- Красива картка статистики з градієнтом
- Детальна інфо по кожному архіву
- ZIP експорт всіх файлів
- Видалення окремих файлів

### 4. **Pull-to-Refresh**

```javascript
document.addEventListener('touchstart', e => {
  if (window.scrollY === 0) {
    pullStartY = e.touches[0].clientY;
    pulling = true;
  }
}, {passive: true});

document.addEventListener('touchend', e => {
  if (!pulling) return;
  const pullDistance = e.changedTouches[0].clientY - pullStartY;
  
  if (pullDistance >= 80) {
    indicator.textContent = '⟳ Оновлення...';
    tg.HapticFeedback.impactOccurred('medium');
    refreshCurrentTab();
  }
});
```

**Працює на всіх вкладках!**

---

## 🔌 API інтеграція

### User Endpoints:

```javascript
// Пошук
POST /api/search
Body: { query: string, user_id: number }
Response: { products: Product[] }

// Додати товар
POST /api/add
Body: { user_id, product_id, quantity }
Response: { success: boolean, message: string }

// Список
GET /api/list/{user_id}
Response: { items: ListItem[], total: number, count: number }

// Зберегти
POST /api/save/{user_id}
Response: { success: boolean, cleared: boolean }

// Архіви
GET /api/archives/{user_id}
Response: { archives: Archive[] }

// ZIP експорт
GET /api/archives/download-all/{user_id}
Response: application/zip

// Статистика
GET /api/statistics/{user_id}
Response: {
  total_lists: number,
  total_amount: number,
  this_month_lists: number,
  popular_department: string
}
```

### Приклад виклику:

```javascript
async function search(query) {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      query: query,
      user_id: userId
    })
  });
  
  const data = await response.json();
  renderSearchResults(data.products);
}
```

---

## 👑 Адмін-панель

### Клікабельні картки статистики:

```javascript
// Картка 1: Всі користувачі
<div class="admin-stat-card" onclick="showAllUsers()">
  <div class="admin-stat-icon">👥</div>
  <div class="admin-stat-value">${data.total_users}</div>
  <div class="admin-stat-label">Користувачів</div>
</div>

// Картка 2: Активні списки
<div class="admin-stat-card success" onclick="showActiveUsers()">
  <div class="admin-stat-icon">🔥</div>
  <div class="admin-stat-value">${data.active_users}</div>
  <div class="admin-stat-label">Активних</div>
</div>

// Картка 3: Товари
<div class="admin-stat-card warning" onclick="showProductsInfo()">
  <div class="admin-stat-icon">📦</div>
  <div class="admin-stat-value">${data.total_products}</div>
  <div class="admin-stat-label">Товарів</div>
</div>

// Картка 4: Резерви
<div class="admin-stat-card danger" onclick="showReservedByDepartment()">
  <div class="admin-stat-icon">💰</div>
  <div class="admin-stat-value">${data.total_reserved_sum} ₴</div>
  <div class="admin-stat-label">Зарезервовано</div>
</div>
```

### Імпорт Excel (Drag & Drop):

```javascript
const dropZone = document.getElementById('dropZone');

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    selectedFile = files[0];
    updateFileInfo();
  }
});

async function uploadFile() {
  const formData = new FormData();
  formData.append('file', selectedFile);
  
  const response = await fetch(
    `/api/admin/import?user_id=${userId}&notify_users=${notifyChecked}`,
    { method: 'POST', body: formData }
  );
  
  const data = await response.json();
  // Показуємо результат: Додано/Оновлено/Деактивовано
}
```

### Примусове збереження:

```javascript
async function forceSave(targetUserId) {
  if (!confirm(`Примусово зберегти список користувача ${targetUserId}?`)) return;
  
  const response = await fetch(
    `/api/admin/force-save/${targetUserId}`,
    {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ user_id: userId })
    }
  );
  
  if (data.success) {
    tg.showAlert('✅ ' + data.message);
    loadAdminActiveUsers();
  }
}
```

### Розсилка:

```javascript
async function sendBroadcast() {
  const message = document.getElementById('broadcastMessage').value.trim();
  
  const response = await fetch(
    `/api/admin/broadcast?user_id=${userId}`,
    {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ user_id: userId, message: message })
    }
  );
  
  // Показуємо alert: Розіслано N користувачам
}
```

---

## 🎨 UI/UX особливості

### 1. **Адаптивна тема**

```css
:root {
  --bg-color: var(--tg-theme-bg-color, #ffffff);
  --text-color: var(--tg-theme-text-color, #000000);
  --button-color: var(--tg-theme-button-color, #0088cc);
  /* ... */
}
```

Автоматично перемикається за темою Telegram!

### 2. **Haptic Feedback**

```javascript
// Успішна дія
tg.HapticFeedback.notificationOccurred('success');

// Pull-to-refresh
tg.HapticFeedback.impactOccurred('medium');

// Помилка
tg.HapticFeedback.notificationOccurred('error');
```

### 3. **Smooth анімації**

```css
.product-card {
  transition: transform 0.2s, background-color 0.3s ease;
}

.product-card:active {
  transform: scale(0.98);
}
```

### 4. **Sticky Header**

```css
.sticky-container {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--bg-color);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
```

### 5. **Центрований заголовок**

```css
h1 {
  text-align: center;
  color: var(--button-color);
}
```

---

## 🚀 Запуск

### Розробка (локально):

```bash
cd webapp
python api.py
# http://localhost:8000
```

### Продакшн (uvicorn):

```bash
uvicorn webapp.api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Продакшн (systemd):

```bash
sudo systemctl start webapp
sudo systemctl enable webapp
sudo systemctl status webapp
```

**Service файл:** `/etc/systemd/system/webapp.service`

```ini
[Unit]
Description=EpicService WebApp API
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/epicservice
Environment="PATH=/home/your_user/epicservice/venv/bin"
ExecStart=/home/your_user/epicservice/venv/bin/uvicorn webapp.api:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📖 Swagger UI

Після запуску доступна автодокументація:

- **Swagger**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🛡️ Безпека

- ✅ `user_id` валідація на кожному ендпоінті
- ✅ ADMIN_IDS перевірка на клієнті та сервері
- ✅ HTTPS only для production
- ✅ CORS налаштовано для Telegram domain
- ✅ CSP headers

---

## 📋 TODO / Roadmap

- [ ] Графіки аналітики (Chart.js)
- [ ] Багатомовність (i18n)
- [ ] Інфінітний скрол для пошуку

---

**Версія:** 2.2.0  
**Остання оновлення:** 25.02.2026

---

"Зроблено в Україні з ❤️"
