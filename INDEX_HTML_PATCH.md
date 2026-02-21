# 🔧 Інструкції для оновлення index.html

Цей файл містить покрокові інструкції для інтеграції функції фото в `webapp/templates/index.html`.

## Крок 1: Додати CSS у <head>

Знайдіть рядок:
```html
<!-- Filters Sidebar -->
<link rel="stylesheet" href="/static/filters-sidebar.css">
```

Додайте ПІСЛЯ нього:
```html
<!-- Photo Feature -->
<link rel="stylesheet" href="/static/css/photos.css">
```

---

## Крок 2: Додати JavaScript перед </body>

Знайдіть рядок:
```html
<!-- Filters Sidebar -->
<link rel="stylesheet" href="/static/filters-sidebar.css">
<script src="/static/filters-sidebar.js"></script>
```

Додайте ПІСЛЯ:
```html
<!-- Photo Feature -->
<script src="/static/js/photos.js"></script>
```

---

## Крок 3: Оновити CSS стилі для product-card

Знайдіть:
```css
.product-card, .list-item, .archive-item, .admin-card { 
    background: var(--secondary-bg-color); 
    border-radius: 12px; 
    padding: 16px; 
    margin-bottom: 12px; 
    cursor: pointer; 
    transition: transform 0.2s, background-color 0.3s ease; 
    position: relative; 
}
```

Замініть `position: relative;` на:
```css
position: relative;
overflow: visible; /* Для стікера фото */
```

---

## Крок 4: Оновити функцію renderProduct()

Знайдіть функцію `renderProduct(p)` (приблизно рядок 280-320).

### 4.1 Додати стікер фото

Знайдіть:
```javascript
const isLocked = p.is_different_department;
const lockedClass = isLocked ? ' locked' : '';
const statusClass = isLocked ? ' locked' : '';
const statusText = isLocked ? '🔒 Заблоковано' : '✅ Знайдено';
```

Додайте ПІСЛЯ:
```javascript
// Стікер фото
const hasPhotos = p.photos && p.photos.length > 0;
const photoIndicator = hasPhotos ? `<span class="photo-badge">📷 ${p.photos.length}</span>` : '';
```

### 4.2 Змінити clickHandler

Знайдіть:
```javascript
const clickHandler = isLocked 
    ? `onclick="showLockedAlert(${p.current_list_department})"` 
    : `onclick='openAddModal(${JSON.stringify(p).replace(/'/g, "&#39;")})>'`;
```

Замініть на:
```javascript
const clickHandler = isLocked 
    ? `onclick="showLockedAlert(${p.current_list_department})"` 
    : `onclick='openModalWithPhotos(${JSON.stringify(p).replace(/'/g, "&#39;")})>'`;
```

### 4.3 Додати стікер у HTML

Знайдіть:
```javascript
return `<div class="product-card${lockedClass}" data-product-id="${p.id}" ${clickHandler}>
    <div class="lock-overlay">🔒</div>
```

Замініть на:
```javascript
return `<div class="product-card${lockedClass}" data-product-id="${p.id}" ${clickHandler}>
    <div class="lock-overlay">🔒</div>
    ${photoIndicator}
```

---

## Крок 5: Оновити функцію search()

Знайдіть функцію `async function search(query)` (приблизно рядок 340).

Знайдіть:
```javascript
const data = await response.json(); 
if (!data.products || data.products.length === 0) { 
    results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено</div>'; 
    cachedProducts = [];
    return; 
}
cachedProducts = data.products.filter(p => p.available > 0);
updateSearchResults();
```

Замініть на:
```javascript
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
```

---

## Крок 6: Додати модальне вікно фотогалереї

Знайдіть:
```html
<div id="addModal" class="modal">...
```

Додайте ПІСЛЯ нього:
```html
<!-- Photo Gallery Modal -->
<div id="photoModal" class="modal">
    <div class="modal-content">
        <div id="photoGallery" class="photo-gallery"></div>
        <div id="photoModalContent"></div>
    </div>
</div>
```

---

## Крок 7: Перейменувати openAddModal (опційно)

Знайдіть:
```javascript
function openAddModal(product) { 
    selectedProduct = product; 
    currentQuantity = 1; 
    ...
}
```

Перейменуйте на `openAddModalOld()` (залишити як backup):
```javascript
function openAddModalOld(product) { 
    // ...
}
```

Нова функція `openModalWithPhotos()` вже є в `photos.js`.

---

## Крок 8: Додати адмінку модерації (опційно)

Знайдіть розділ `<!-- Admin Tab -->` та додайте перед розділом "📥 Імпорт товарів":

```html
<div class="admin-section-title">🖼️ Модерація фото</div>
<div id="photoModeration">
    <div class="loader">Завантаження...</div>
</div>
<div class="action-buttons">
    <button class="btn btn-primary" onclick="loadPhotoModeration()">🔄 Оновити</button>
</div>
```

Та додайте функції в кінці `<script>` (div. INTEGRATION_GUIDE.md).

---

## Перевірка

Після всіх змін:

1. Перезапустіть webapp: `python webapp/api.py`
2. Відкрийте міні-апп в Telegram
3. Знайдіть товар → натисніть на картку
4. Ви побачите кнопку "📷 Додати фото"
5. Завантажте фото та перевірте галерею

---

## Альтернатива: Автоматичний патч

Якщо ви маєте доступ до репозиторію локально:

```bash
git checkout feature/product-photos
git pull origin feature/product-photos

# Використати текстовий редактор для заміни в index.html
```

Або я можу створити повністю оновлений index.html з всіма змінами.
