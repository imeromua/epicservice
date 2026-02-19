# Changelog

Всі значні зміни в проекті EpicService будуть задокументовані в цьому файлі.

Формат заснований на [Keep a Changelog](https://keepachangelog.com/uk/1.0.0/),
і проект дотримується [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-02-19

### ✨ Added (New Features)

#### PWA (Progressive Web App)
- 📱 **PWA Support** - Mini App тепер можна встановити як нативний додаток
- 📦 **Service Worker** - офлайн кешування статичних ресурсів
- 🌐 **Manifest.json** - конфігурація PWA з іконками та splash screen
- 📢 **Install Banner** - автоматичний банер встановлення
- 🔌 **Offline Indicator** - індикатор відсутності зв'язку
- 🔄 **PWA Redirect** - логіка виявлення PWA режиму

#### User Features
- 🔄 **Pull-to-Refresh** - оновлення свайпом на всіх вкладках
- 📊 **User Statistics** - персональна статистика з красивою карткою-градієнтом
- 📦 **ZIP Export** - завантаження всіх архівів одним файлом
- 📁 **Archive Stats** - детальна статистика кожного архіву
- ⚡ **Haptic Feedback** - вібраційний відгук на дії
- 🌓 **Adaptive Theme** - автоматична темна/світла тема

#### Admin Features
- 📊 **Advanced Analytics** - детальна статистика з клікабельними картками
- 💾 **Force Save** - примусове збереження списків користувачів
- 📢 **Broadcast** - масова розсилка повідомлень
- 📊 **Users Modal** - модальні вікна зі списками користувачів
- 📈 **Reserved by Department** - візуалізація резервів по відділах
- 📦 **ZIP All Archives** - завантаження всіх архівів всіх юзерів
- 👾 **Drag & Drop** - перетягування Excel файлів для імпорту

#### API Endpoints
- `GET /api/statistics/{user_id}` - статистика користувача
- `GET /api/archive/stats/{filename}` - статистика архіву
- `GET /api/archives/download-all/{user_id}` - ZIP експорт для юзера
- `GET /api/list/department/{user_id}` - поточний відділ
- `GET /api/admin/users/all` - всі користувачі
- `GET /api/admin/users/active` - активні списки
- `GET /api/admin/products/info` - інфо про товари
- `GET /api/admin/reserved/by-department` - резерви по відділах
- `POST /api/admin/force-save/{user_id}` - примусове збереження
- `POST /api/admin/broadcast` - розсилка
- `GET /api/admin/archives/download-all` - ZIP всіх архівів

#### Documentation
- 📖 **README.md** - повна документація проекту
- 🌐 **webapp/README.md** - документація frontend
- 🔒 **PRIVACY_POLICY.md** - оновлена політика (PWA, офлайн)
- 🔧 **TECHNICAL_GUIDE.md** - розширений технічний гайд
- 📚 **USER_GUIDE.md** - оновлена інструкція користувача
- ⚙️ **.env.example** - додано WEBAPP_URL та інші змінні
- 🚀 **deploy/** - додано nginx.conf та epicservice.service
- 📝 **CHANGELOG.md** - цей файл!

### 🔧 Changed (Improvements)

#### UI/UX
- 🎨 **Centered Title** - заголовок тепер відцентрований
- 📊 **Better Stats Card** - красива картка з градієнтом
- 📋 **Improved List View** - покращений вигляд списку
- 🔒 **Visual Locking** - покращена візуалізація блокування (grayscale + 🔒)
- 📱 **Mobile Optimizations** - оптимізація для мобільних

#### Performance
- ⚡ **Faster Loading** - швидше завантаження через Service Worker
- 📦 **Better Caching** - покращене кешування статичних ресурсів
- 🔍 **Debounce Search** - 500ms debounce для пошуку

#### Backend
- 📊 **Statistics Queries** - нові SQL запити для статистики
- 📦 **ZIP Generation** - генерація ZIP архівів
- 🔒 **Better Error Handling** - покращена обробка помилок

### 🔒 Security
- 🔐 **Enhanced HTTPS** - TLS 1.3 тільки
- 🛡️ **Security Headers** - HSTS, CSP, X-Frame-Options
- 🔒 **PWA Security** - Service Worker тільки через HTTPS

### 📝 Documentation
- 📖 **Complete Rewrite** - повне переписання документації
- 🔍 **Better Examples** - більше прикладів коду
- 💡 **Troubleshooting** - розширений troubleshooting

---

## [1.0.0] - 2025-12-15

### ✨ Added
- 🤖 **Telegram Bot** - основний бот на aiogram 3.x
- 🌐 **Mini App** - Telegram WebApp з Vanilla JS
- 🔍 **Search** - пошук товарів за артикулом/назвою
- 📋 **List Management** - створення та редагування списків
- 🔒 **Department Locking** - блокування відділів
- 💾 **Save to Excel** - збереження в Excel
- 📁 **Archives** - історія збережених списків
- 📈 **Reservations** - резервування товарів
- 👑 **Admin Panel** - адміністративна панель
- 📥 **Excel Import** - імпорт товарів
- 📤 **Export Reports** - експорт звітів
- 📊 **Basic Statistics** - базова статистика
- 🗄️ **PostgreSQL** - реляційна база даних
- 📦 **Redis** - FSM storage
- 🔄 **Archive Rotation** - ротація файлів (10 файлів/user)
- 🗑️ **Auto Cleanup** - автоочищення trash/ (14 днів)

---

## 🔗 Посилання

- **GitHub Repository**: https://github.com/imeromua/epicservice
- **Documentation**: README.md, TECHNICAL_GUIDE.md, USER_GUIDE.md
- **Contact**: imerom25@gmail.com | @my_life_ukr

---

## 📌 Легенда

- ✨ **Added** - нові функції
- 🔧 **Changed** - зміни в існуючому функціоналі
- 🐛 **Fixed** - виправлені помилки
- 🛡️ **Security** - зміни в безпеці
- 🛑 **Deprecated** - застарілі функції
- 🗑️ **Removed** - видалені функції
