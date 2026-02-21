# Гід з інтеграції функції фото

## Крок 1: Оновити index.html

### 1.1 Додати CSS стилі

У `webapp/templates/index.html` додайте перед `</head>`:

```html
<!-- Photo styles -->
<link rel="stylesheet" href="/static/css/photos.css">
```

### 1.2 Додати JavaScript

Перед закриваючим `</body>` додайте:

```html
<!-- Photo functionality -->
<script src="/static/js/photos.js"></script>
```

### 1.3 Оновити функцію renderProduct

Знайдіть функцію `renderProduct(p)` та додайте стікер фото після `<div class="lock-overlay">`:

```javascript
function renderProduct(p) {
    const isLocked = p.is_different_department;
    const lockedClass = isLocked ? ' locked' : '';
    const statusClass = isLocked ? ' locked' : '';
    const statusText = isLocked ? '🔒 Заблоковано' : '✅ Знайдено';
    
    // Додати цю частину:
    const hasPhotos = p.photos && p.photos.length > 0;
    const photoIndicator = hasPhotos ? `<span class="photo-badge">📷 ${p.photos.length}</span>` : '';
    
    const clickHandler = isLocked 
        ? `onclick="showLockedAlert(${p.current_list_department})"` 
        : `onclick='openModalWithPhotos(${JSON.stringify(p).replace(/'/g, "&#39;")})'`; // Змінити на openModalWithPhotos
    
    return `<div class="product-card${lockedClass}" data-product-id="${p.id}" ${clickHandler}>
        <div class="lock-overlay">🔒</div>
        ${photoIndicator}
        <!-- решта коду без змін -->
    </div>`;
}
```

### 1.4 Замінити openAddModal на openModalWithPhotos

Знайдіть функцію `openAddModal` та перейменуйте її на `openAddModalOld` (залишити як backup).

Нова функція `openModalWithPhotos` вже є в `photos.js`.

### 1.5 Оновити функцію search

У функції `search(query)` після отримання даних додайте завантаження фото:

```javascript
async function search(query) { 
    const results = document.getElementById('searchResults'); 
    results.innerHTML = '<div class="loader">🔍 Пошук...</div>'; 
    try { 
        const response = await fetch('/api/search', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({query, user_id: userId}) 
        }); 
        const data = await response.json(); 
        
        if (!data.products || data.products.length === 0) { 
            results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено</div>'; 
            cachedProducts = [];
            return; 
        }
        
        // Завантаження фото для кожного товару
        for (let product of data.products) {
            product.photos = await loadProductPhotos(product.article);
        }
        
        cachedProducts = data.products.filter(p => p.available > 0);
        updateSearchResults();
    } catch (error) { 
        results.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка пошуку</div>'; 
        cachedProducts = [];
    } 
}
```

## Крок 2: Підключити API роутер

У `webapp/api.py` додайте:

```python
from webapp.routers import photos

app.include_router(photos.router)
```

## Крок 3: Створити директорії

```bash
mkdir -p webapp/static/uploads/photos
mkdir -p webapp/temp_files
```

Або у `.gitignore` вже є ці шляхи, тому вони створяться автоматично при першому завантаженні.

## Крок 4: Застосувати міграцію

```bash
alembic upgrade head
```

## Крок 5: Додати адмінпанель модерації

У секції адмінки (`adminContent`) додайте новий розділ:

```html
<div class="admin-section-title">🖼️ Модерація фото</div>
<div id="photoModeration">
    <div class="loader">Завантаження...</div>
</div>
<div class="action-buttons">
    <button class="btn btn-primary" onclick="loadPhotoModeration()">🔄 Оновити</button>
</div>
```

Та додайте функцію завантаження:

```javascript
async function loadPhotoModeration() {
    if (!isAdmin) return;
    
    const container = document.getElementById('photoModeration');
    container.innerHTML = '<div class="loader">Завантаження...</div>';
    
    try {
        const response = await fetch(`/api/photos/moderation/pending?user_id=${userId}`);
        const data = await response.json();
        
        if (!data.photos || data.photos.length === 0) {
            container.innerHTML = '<div class="empty-state">🎉 Немає фото на модерацію</div>';
            return;
        }
        
        let html = '';
        for (const photo of data.photos) {
            html += `
                <div class="moderation-item">
                    <img src="/static/${photo.file_path}" alt="Product" class="moderation-photo">
                    <div class="moderation-details">
                        <strong>📦 ${photo.article}</strong> - ${photo.product_name}<br>
                        👤 ${photo.uploaded_by}<br>
                        📅 ${photo.uploaded_at}<br>
                        📊 ${(photo.file_size / 1024).toFixed(1)} KB (було ${(photo.original_size / 1024 / 1024).toFixed(1)} MB)
                    </div>
                    <div class="moderation-actions">
                        <button class="btn btn-success" onclick="moderatePhoto(${photo.id}, 'approved')">✅ Схвалити</button>
                        <button class="btn btn-danger" onclick="moderatePhoto(${photo.id}, 'rejected')">❌ Відхилити</button>
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = '<div class="empty-state">❌ Помилка завантаження</div>';
    }
}

async function moderatePhoto(photoId, status) {
    const reason = status === 'rejected' ? prompt('Вкажіть причину відхилення:') : null;
    
    try {
        const formData = new FormData();
        formData.append('status', status);
        if (reason) formData.append('reason', reason);
        formData.append('user_id', userId);
        
        const response = await fetch(`/api/photos/moderation/${photoId}`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            tg.showAlert('✅ ' + data.message);
            loadPhotoModeration();
        } else {
            tg.showAlert('❌ Помилка');
        }
    } catch (error) {
        tg.showAlert('❌ Помилка: ' + error.message);
    }
}
```

## Крок 6: Перевірка

1. Запустіть сервер
2. Відкрийте міні-апп
3. Знайдіть товар
4. Натисніть на картку
5. Натисніть "📷 Додати фото"
6. Завантажте фото
7. Перейдіть в адмінку для модерації

## Зауваження

- **Важливо:** Фото зберігаються за артикулом товару
- Фото автоматично стискаються до ~500KB
- Максимум 3 фото на товар
- Фото не включаються в звіти та експорт
