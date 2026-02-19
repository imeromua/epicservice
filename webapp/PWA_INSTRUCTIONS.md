# PWA (Установка та тестування)

## 🚀 Що було додано

### 1. Основні файли:
- **manifest.json** - конфігурація PWA (назва, іконки, кольори, shortcuts)
- **sw.js** - Service Worker для кешування та офлайн режиму
- **pwa-install.js** - скрипт для встановки та оновлень
- **pwa-styles.css** - стилі для PWA UI елементів

### 2. Що потрібно зробити:

#### А. Оновити `index.html`

Додати в `<head>` секцію:

```html
<!-- PWA Meta Tags -->
<meta name="theme-color" content="#3b82f6">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="EpicService">

<!-- Manifest -->
<link rel="manifest" href="/static/manifest.json">

<!-- Icons for iOS -->
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/icon-192x192.png">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/icon-192x192.png">
<link rel="icon" type="image/png" sizes="16x16" href="/static/icons/icon-192x192.png">

<!-- PWA Styles -->
<link rel="stylesheet" href="/static/pwa-styles.css">
```

Додати перед закриваючим `</body>`:

```html
<!-- PWA Install Banner (опціонально) -->
<div id="pwa-install-banner" class="pwa-install-banner">
  <div class="pwa-install-content">
    <span>📱 Встановіть Epic Service на свій телефон!</span>
    <button id="pwa-install-btn" class="btn btn-primary">Встановити</button>
    <button onclick="this.parentElement.parentElement.style.display='none'" class="btn btn-secondary">Пізніше</button>
  </div>
</div>

<!-- Offline Indicator -->
<div id="offline-indicator" class="offline-indicator">
  ⚠️ Немає з'єднання з інтернетом
</div>

<!-- PWA Scripts -->
<script src="/static/pwa-install.js"></script>

<!-- Offline Detection -->
<script>
  window.addEventListener('online', () => {
    document.getElementById('offline-indicator').classList.remove('show');
  });
  
  window.addEventListener('offline', () => {
    document.getElementById('offline-indicator').classList.add('show');
  });
  
  // Перевірка при завантаженні
  if (!navigator.onLine) {
    document.getElementById('offline-indicator').classList.add('show');
  }
</script>
```

#### Б. Створити іконки

Див. інструкції в `/webapp/static/icons/README.md`

Швидкий спосіб (для тестування):
1. Ідіть на https://favicon.io/emoji-favicons/
2. Оберіть emoji: 🔧 (гайковий ключ) або ⚙️ (шестеренка)
3. Завантажте та розмістіть в `/webapp/static/icons/`

#### В. Оновити FastAPI (api.py)

Перевірте, що static файли віддаються коректно:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
```

## 🧪 Тестування

### 1. На Android:

1. Відкрийте сайт в Chrome
2. Натисніть на меню (три крапки)
3. Оберіть "Встановити додаток" / "Install app"
4. Підтвердіть встановку

Або використайте банер встановки на сайті.

### 2. Перевірка через Chrome DevTools:

```
1. Відкрийте DevTools (F12)
2. Application tab
3. Перевірте:
   - Manifest: чи завантажується manifest.json
   - Service Workers: чи зареєстрований sw.js
   - Cache Storage: чи файли кешуються
```

### 3. Lighthouse PWA Audit:

```
1. Chrome DevTools > Lighthouse
2. Оберіть "Progressive Web App"
3. Натисніть "Generate report"
4. Перевірте скоринг (повинно бути > 90)
```

## ✅ Що працює

- ✅ Встановка як додаток на Android
- ✅ Іконка на головному екрані
- ✅ Запуск без браузерної панелі (standalone mode)
- ✅ Офлайн режим з кешем
- ✅ Автоматичні оновлення
- ✅ Shortcuts (швидкі дії з іконки)
- ✅ Індикатор офлайн режиму
- ✅ Сповіщення про оновлення

## 🔧 Налаштування

### Змінити кольори теми:

В `manifest.json`:
```json
"theme_color": "#3b82f6",
"background_color": "#1e293b"
```

### Змінити назву:

В `manifest.json`:
```json
"name": "Epic Service",
"short_name": "EpicService"
```

### Додати більше shortcuts:

В `manifest.json` додайте до масиву `shortcuts`.

## 🚀 Публікація

### Для HTTPS обов'язково:
PWA працює **тільки по HTTPS** (або localhost для тестування).

Якщо використовуєте ngrok, nginx або cloudflare - переконайтеся, що SSL налаштований.

### Оновлення версії:

1. Змініть `CACHE_NAME` в `sw.js`:
```javascript
const CACHE_NAME = 'epicservice-v1.0.1'; // збільшіть версію
```

2. Користувачі отримають автоматичне повідомлення про оновлення.

## 📊 Моніторинг

Додати Google Analytics або іншу аналітику для відстеження:
- Кількості установок
- Використання в offline режимі
- Популярності shortcuts

---

🎉 **Ваш Epic Service тепер повноцінний PWA!**
