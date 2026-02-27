# Changelog

Всі значні зміни в проекті EpicService будуть задокументовані в цьому файлі.

Формат заснований на [Keep a Changelog](https://keepachangelog.com/uk/1.0.0/),
і проект дотримується [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.0] - 2026-02-27

### 🗑️ Removed — Очищення застарілого коду бота

#### Причина
> Після повного переходу функціоналу користувача у Telegram Mini App (WebApp), хендлери бота
> для роботи зі списками, пошуком та архівом були виведені з реєстрації в `bot.py`.
> Ці файли більше не виконували жодної функції і залишались мертвим кодом у репозиторії.

#### Видалені файли
- 🗑️ `handlers/user/list_editing.py` — редагування списку через бот (замінено WebApp)
- 🗑️ `handlers/user/list_management.py` — управління списком через бот (замінено WebApp)
- 🗑️ `handlers/user/list_saving.py` — збереження списку через бот (замінено WebApp)
- 🗑️ `handlers/user/__init__.py` — порожній init файл пакету
- 🗑️ `handlers/user_search.py` — пошук товарів через бот (замінено WebApp)
- 🗑️ `handlers/archive.py` — архів через бот (замінено WebApp)
- 🗑️ `utils/card_generator.py` — генерація карток товарів (використовувалась лише deprecated user_search.py)

#### Очищено `lexicon/lexicon.py`
- Видалено ~90 текстових констант, що використовувались виключно у видалених хендлерах
- Залишено лише константи, що використовуються в активному коді (адмін-панель, обробники помилок)

### 📝 Updated — Документація

- Оновлено `README.md`: схема архітектури без deprecated файлів, прибрано "Мобільний додаток (React Native)" з Roadmap, версія → 2.3.0
- Оновлено `TECHNICAL_GUIDE.md`: схема структури проекту без deprecated файлів, версія → 2.3.0

### 📈 Результат
- Прибрано 7 файлів / ~700 рядків мертвого коду
- Очищено ~90 невикористовуваних констант з лексикону
- Кодова база відповідає реальній архітектурі: весь user-функціонал знаходиться у WebApp

---

## [2.2.0] - 2026-02-23

### 🗑️ Removed — PWA повністю видалено

#### Причина
> Telegram Mini App потребує `window.Telegram.WebApp` для авторизації користувача. Без Telegram-контексту
> `userId` завжди = 0, а додаток працював лише як редирект на `t.me/epic016_bot/webapp`.
> PWA без авторизації = мертвий функціонал. Додаток повинен працювати тільки всередині Telegram.

#### Видалені файли
- 🗑️ `webapp/static/sw.js` — Service Worker
- 🗑️ `webapp/static/manifest.json` — PWA manifest
- 🗑️ `webapp/static/css/pwa-styles.css` — стилі банеру встановки, офлайн-індикатора, анімацій
- 🗑️ `webapp/static/js/pwa-redirect.js` — редирект на Telegram
- 🗑️ `webapp/static/js/pwa-install.js` — логіка встановки PWA

#### Видалено з `index.html`
- Скрипт `pwa-redirect.js` (з позначкою `MUST BE FIRST`)
- PWA Meta Tags: `theme-color`, `mobile-web-app-capable`, `apple-mobile-web-app-*`
- `<link rel="manifest">`
- Apple touch icon та PNG icon лінки
- `<link rel="stylesheet" href="pwa-styles.css">`
- PWA Install Banner `div`
- Offline Indicator `div`
- `<script src="pwa-install.js">`
- Offline/Online Detection `<script>` блок

### 📈 Результат
- `index.html` зменшився на ~60 рядків
- Прибрано 5 файлів / ~500 рядків мертвого коду
- Додаток запускається виключно в Telegram WebApp контексті

---

## [2.1.0] - 2026-02-23

### 🔧 Changed (Refactoring & Cleanup)

#### PWA / Service Worker
- 🔄 **SW Cache bump** — версія кешу піднята з `v1.0.1` до `v1.1.0`

#### Static Files Structure
- 📁 **Переміщено до `static/js/`** — `pwa-redirect.js`, `pwa-install.js`, `filters-sidebar.js`
- 🎨 **Переміщено до `static/css/`** — `pwa-styles.css`, `filters-sidebar.css`
- 🔗 **Оновлено посилання** в `index.html`
- 🗑️ **Видалено** `debug_archives.py`, `update-html.py`

#### Fixes
- 🐛 Виправлено транслітерацію в console.log офлайн/онлайн подіях
- 🐛 Оновлено опис в `index.html` і `manifest.json` (відповідно до боту `@epic016_bot`)
- 🐛 Виправлено placeholder `your_bot_name` → `epic016_bot` в manifest shortcuts

---

## [2.0.0] - 2026-02-19

### ✨ Added (New Features)

#### PWA (Progressive Web App)
- 📱 **PWA Support** - Mini App тепер можна встановити як нативний додаток
- 📦 **Service Worker** - офлайн кешування статичних ресурсів
- 🌐 **Manifest.json** - конфігурація PWA
- 📢 **Install Banner** - автоматичний банер встановлення
- 🔌 **Offline Indicator** - індикатор відсутності зв'язку
- 🔄 **PWA Redirect** - логіка виявлення PWA режиму

#### User Features
- 🔄 **Pull-to-Refresh** - оновлення свайпом на всіх вкладках
- 📊 **User Statistics** - персональна статистика
- 📦 **ZIP Export** - завантаження всіх архівів одним файлом
- 📁 **Archive Stats** - детальна статистика кожного архіву
- ⚡ **Haptic Feedback** - вібраційний відгук на дії
- 🌓 **Adaptive Theme** - автоматична темна/світла тема

#### Admin Features
- 📊 **Advanced Analytics** - детальна статистика
- 💾 **Force Save** - примусове збереження списків
- 📢 **Broadcast** - масова розсилка повідомлень
- 📊 **Users Modal** - модальні вікна зі списками
- 📈 **Reserved by Department** - візуалізація резервів
- 📦 **ZIP All Archives** - завантаження всіх архівів
- 👾 **Drag & Drop** - імпорт Excel

#### API Endpoints
- `GET /api/statistics/{user_id}`
- `GET /api/archive/stats/{filename}`
- `GET /api/archives/download-all/{user_id}`
- `GET /api/list/department/{user_id}`
- `GET /api/admin/users/all`
- `GET /api/admin/users/active`
- `GET /api/admin/products/info`
- `GET /api/admin/reserved/by-department`
- `POST /api/admin/force-save/{user_id}`
- `POST /api/admin/broadcast`
- `GET /api/admin/archives/download-all`

### 🔧 Changed
- 🎨 Centered Title, Better Stats Card, Improved List View
- ⚡ Faster Loading, Better Caching, Debounce Search 500ms
- 📊 Statistics Queries, ZIP Generation, Better Error Handling

### 🔒 Security
- TLS 1.3, HSTS, CSP, X-Frame-Options

---

## [1.0.0] - 2025-12-15

### ✨ Added
- 🤖 **Telegram Bot** - основний бот на aiogram 3.x
- 🌐 **Mini App** - Telegram WebApp з Vanilla JS
- 🔍 **Search** - пошук товарів
- 📋 **List Management** - списки
- 🔒 **Department Locking** - блокування відділів
- 💾 **Save to Excel**
- 📁 **Archives** - історія списків
- 📈 **Reservations**
- 👑 **Admin Panel**
- 📥 **Excel Import**
- 📤 **Export Reports**
- 📊 **Basic Statistics**
- 🗄️ **PostgreSQL**
- 📦 **Redis** - FSM storage
- 🔄 **Archive Rotation** (10 файлів/user)
- 🗑️ **Auto Cleanup** trash/ (14 днів)

---

## 🔗 Посилання

- **GitHub**: https://github.com/imeromua/epicservice
- **Bot**: https://t.me/epic016_bot
- **Contact**: imerom25@gmail.com | @my_life_ukr

---

## 📌 Легенда

- ✨ **Added** — нові функції
- 🔧 **Changed** — зміни в існуючому
- 🐛 **Fixed** — виправлені помилки
- 🛡️ **Security** — зміни в безпеці
- 🛑 **Deprecated** — застарілі
- 🗑️ **Removed** — видалені

---

"Зроблено в Україні з ❤️"
