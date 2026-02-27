# EpicService — Android-додаток

## Зміст

1. [Огляд](#огляд)
2. [Архітектура](#архітектура)
3. [Вимоги](#вимоги)
4. [Авторизація за номером телефону](#авторизація-за-номером-телефону)
5. [Структура проекту](#структура-проекту)
6. [Налаштування та збірка](#налаштування-та-збірка)
7. [Офлайн-режим](#офлайн-режим)
8. [API-документація](#api-документація)
9. [Конфігурація сервера](#конфігурація-сервера)
10. [Безпека](#безпека)
11. [Усунення неполадок](#усунення-неполадок)

---

## Огляд

**EpicService Android** — нативний Android-додаток для корпоративного складського обліку.

Ключові можливості:
- 📱 Авторизація за номером телефону (+380...) з OTP-кодом через Telegram-бот
- 🔍 Пошук товарів за артикулом та назвою
- 📋 Складання та збереження списків замовлень
- 📁 Перегляд архіву збережених списків
- 📵 Повноцінна офлайн-робота (кешовані дані)
- 🔐 Біометрична автентифікація (відбиток пальця / обличчя)
- 🛡️ Адміністративна панель (для admin/superadmin)

---

## Архітектура

```
android-app/
├── www/                    # Веб-шар (HTML/CSS/JS)
│   ├── index.html          # Головний HTML (auth + app screens)
│   ├── css/app.css         # Стилі (dark theme, mobile-first)
│   ├── js/
│   │   ├── api.js          # HTTP-клієнт + офлайн-кешування
│   │   ├── phone-auth.js   # Модуль авторизації
│   │   └── app.js          # Головний модуль (вкладки, пошук, список)
│   ├── manifest.json       # PWA manifest
│   └── sw.js               # Service Worker (офлайн)
└── android/                # Нативний Android-проект (Capacitor)
    └── app/src/main/
        ├── java/ua/epicservice/app/
        │   ├── MainActivity.kt         # Точка входу (extends BridgeActivity)
        │   └── EpicServicePlugin.kt    # Нативний Capacitor-плагін
        ├── AndroidManifest.xml
        └── res/values/
            ├── strings.xml
            ├── colors.xml
            └── styles.xml
```

**Технологічний стек:**
- [Capacitor 6](https://capacitorjs.com/) — міст між веб і нативним Android
- Kotlin — нативні функції (біометрія, вібрація)
- Vanilla JavaScript — бізнес-логіка та UI
- CSS Custom Properties — адаптивна dark-тема
- Service Worker — офлайн-підтримка

---

## Вимоги

### Для розробки
- Node.js ≥ 18
- Android Studio ≥ Hedgehog (2023.1.1)
- Android SDK (API 26+)
- JDK 17
- Python 3.11+ (для бекенду)

### Для пристрою / емулятора
- Android 8.0 (API 26) або вище
- Інтернет-з'єднання (для першого входу)

---

## Авторизація за номером телефону

### Як це працює

```
Користувач (Android-додаток)      Сервер (FastAPI)       Telegram-бот
         |                               |                     |
         |--- 1. POST /api/auth/phone/request (phone) -------> |
         |                               |                     |
         |                               |-- 2. Генерує OTP   |
         |                               |-- 3. Зберігає в Redis (TTL=5хв)
         |                               |                     |
         |                               |--- 4. send_message(chat_id, OTP) -> |
         |                               |                     |-- 5. Отримує код
         |                               |                     |
         |<--- 6. { "sent_via_bot": true } -------------------|
         |                               |                     |
         |--- 7. POST /api/auth/phone/verify (phone, otp) ---> |
         |                               |                     |
         |                               |-- 8. Перевіряє OTP в Redis
         |                               |-- 9. Знаходить/створює User
         |                               |-- 10. Генерує JWT токени
         |                               |                     |
         |<--- 11. { access_token, refresh_token, user } ------|
```

### Прив'язка телефону до бот-акаунту

Щоб отримувати OTP-коди через Telegram-бот, користувач повинен прив'язати свій номер телефону:

1. Відкрийте Telegram-бот EpicService
2. Надішліть команду `/linkphone`
3. Натисніть кнопку **"📱 Поділитися номером"**
4. Telegram підтвердить прив'язку

**Після прив'язки:** при вході в Android-додаток OTP-код буде автоматично надіслано у Telegram-бот.

### Перший вхід (новий користувач)

Якщо номер телефону не знайдено в базі:
1. Додаток попросить ввести **ім'я**
2. Буде створено новий акаунт зі статусом `pending`
3. Адміністратор має підтвердити доступ
4. Після підтвердження можна користуватися всіма функціями

### Формат номера телефону

Підтримуються формати (автоматична нормалізація до `+380XXXXXXXXX`):
- `+380XXXXXXXXX` — міжнародний формат
- `0XXXXXXXXX` — без коду країни
- `380XXXXXXXXX` — без +

---

## Структура проекту

```
android-app/
├── package.json            # npm-залежності (Capacitor)
├── capacitor.config.json   # Конфігурація Capacitor
├── www/                    # Веб-активи (вхідна точка додатку)
│   ├── index.html
│   ├── manifest.json
│   ├── sw.js
│   ├── css/
│   │   └── app.css
│   └── js/
│       ├── api.js          # HTTP-клієнт
│       ├── phone-auth.js   # Авторизація
│       └── app.js          # Головний модуль
└── android/
    ├── build.gradle        # Кореневий Gradle
    ├── variables.gradle    # Версії залежностей
    ├── settings.gradle
    ├── gradle.properties
    └── app/
        ├── build.gradle    # Gradle модуля app
        ├── capacitor.build.gradle
        └── src/main/
            ├── AndroidManifest.xml
            ├── java/ua/epicservice/app/
            │   ├── MainActivity.kt
            │   └── EpicServicePlugin.kt
            └── res/values/
                ├── strings.xml
                ├── colors.xml
                └── styles.xml
```

---

## Налаштування та збірка

### 1. Клонування та встановлення залежностей

```bash
# Перейдіть до директорії android-app
cd android-app

# Встановіть npm-залежності (Capacitor)
npm install
```

### 2. Налаштування URL сервера

Відкрийте `www/index.html` і знайдіть або додайте перед першим `<script>`:

```html
<script>
window.APP_CONFIG = {
    serverUrl: 'https://anubis-ua.pp.ua'
};
</script>
```

Або через `capacitor.config.json` (якщо використовуєте живий сервер):

```json
{
  "server": {
    "url": "https://anubis-ua.pp.ua",
    "cleartext": false
  }
}
```

### 3. Синхронізація з Android

```bash
# Синхронізує веб-активи та плагіни з Android-проектом
npx cap sync android

# Відкриває проект в Android Studio
npx cap open android
```

### 4. Збірка APK

**Debug APK:**
```bash
cd android
./gradlew assembleDebug
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

**Release APK (потрібен keystore):**
```bash
# 1. Створіть keystore (один раз)
keytool -genkey -v -keystore epicservice.keystore \
    -alias epicservice -keyalg RSA -keysize 2048 -validity 10000

# 2. Налаштуйте signingConfigs в app/build.gradle
# 3. Збудуйте
./gradlew assembleRelease
# APK: android/app/build/outputs/apk/release/app-release.apk
```

### 5. Запуск на пристрої/емуляторі

```bash
npx cap run android
```

---

## Офлайн-режим

Додаток повністю підтримує роботу без інтернету:

| Функція | Онлайн | Офлайн |
|---------|--------|--------|
| Пошук товарів | ✅ Реальні дані | ✅ Кешовані (5 хв) |
| Список замовлень | ✅ Збереження на сервер | ✅ Тільки локально |
| Перегляд архіву | ✅ Реальні дані | ✅ Кешовані |
| Авторизація | ✅ OTP/пароль | ✅ Збережений токен |

**Технічна реалізація:**
- `localStorage` — зберігання JWT-токенів та кешу
- `Service Worker` — кешування статичних ресурсів
- `navigator.onLine` + `window.online/offline` — моніторинг мережі

---

## API-документація

### Авторизація за телефоном

#### POST `/api/auth/phone/request`

Відправляє OTP-код на номер телефону.

**Тіло запиту:**
```json
{
  "phone": "+380991234567"
}
```

**Відповідь:**
```json
{
  "success": true,
  "phone": "+380991234567",
  "registered": true,
  "sent_via_bot": true,
  "message": "Код надіслано в Telegram-бот"
}
```

| Поле | Тип | Опис |
|------|-----|------|
| `registered` | bool | `true` якщо номер вже зареєстрований |
| `sent_via_bot` | bool | `true` якщо OTP надіслано у Telegram-бот |

---

#### POST `/api/auth/phone/verify`

Перевіряє OTP та повертає JWT-токени.

**Тіло запиту:**
```json
{
  "phone": "+380991234567",
  "otp": "123456",
  "first_name": "Іван"
}
```

> `first_name` — обов'язкове лише для нових користувачів (`registered: false`).

**Відповідь:**
```json
{
  "success": true,
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {
    "id": 12345678,
    "phone": "+380991234567",
    "first_name": "Іван",
    "role": "user",
    "status": "pending"
  }
}
```

**Помилки:**
- `400` — Невірний або протермінований код
- `429` — Забагато спроб (заблоковано на 15 хвилин)
- `503` — Redis недоступний

---

#### POST `/api/auth/login`

Вхід за логіном та паролем (запасний варіант).

**Тіло запиту:**
```json
{
  "login": "user123",
  "password": "password"
}
```

---

#### POST `/api/auth/register`

Реєстрація нового користувача з логіном та паролем.

**Тіло запиту:**
```json
{
  "login": "user123",
  "password": "password",
  "first_name": "Іван"
}
```

---

#### POST `/api/auth/refresh`

Оновлення access-токена.

**Тіло запиту:**
```json
{
  "refresh_token": "eyJ..."
}
```

---

#### GET `/api/auth/me`

Отримання інформації про поточного користувача.

**Заголовок:** `Authorization: Bearer <access_token>`

---

### Роль та статус користувача

| Роль | Доступ |
|------|--------|
| `user` | Пошук, список, архів |
| `moderator` | + Модерація фото |
| `admin` | + Адмін-панель |
| `superadmin` | Повний доступ |

| Статус | Значення |
|--------|----------|
| `pending` | Очікує підтвердження адміністратора |
| `active` | Повний доступ |
| `blocked` | Доступ заблоковано |

---

## Конфігурація сервера

Домен сервера: **`anubis-ua.pp.ua`**

Необхідні змінні оточення (`.env` на сервері):

```env
# Сервер
SERVER_URL=https://anubis-ua.pp.ua
WEBAPP_URL=https://anubis-ua.pp.ua

# JWT (обов'язково змінити!)
JWT_SECRET_KEY=your-very-secret-key-here

# Redis (для OTP)
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

### CORS налаштування

Для роботи мобільного додатку необхідно дозволити CORS:

```python
# webapp/api.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anubis-ua.pp.ua", "capacitor://localhost", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Capacitor: підключення до живого сервера

Для розробки можна налаштувати Capacitor на прямий сервер (без локальних активів):

```json
// capacitor.config.json
{
  "server": {
    "url": "https://anubis-ua.pp.ua/standalone",
    "cleartext": false
  }
}
```

---

## Безпека

### JWT токени
- Access token: 24 години
- Refresh token: 30 днів
- Алгоритм: HS256

### OTP захист
- Довжина коду: 6 цифр
- Термін дії: 5 хвилин
- Максимум спроб: 5 (блокування на 15 хвилин)
- Одноразовий (видаляється після успішної перевірки)

### Мережева безпека
- `android:usesCleartextTraffic="false"` — тільки HTTPS
- Certificate pinning (додатково — через OkHttp або Network Security Config)

### Зберігання даних
- JWT токени зберігаються в `localStorage`
- Для підвищення безпеки рекомендується використовувати `@capacitor/preferences` (зашифроване сховище)

### Biometric Auth
- Використовує `androidx.biometric` (API 26+)
- Підтримує відбиток пальця та Face Unlock
- Fallback на PIN/пароль пристрою

---

## Усунення неполадок

### OTP не надходить у Telegram-бот

1. Переконайтеся, що прив'язали номер через `/linkphone` у боті
2. Перевірте, чи активований бот (надішліть `/start`)
3. Переконайтеся, що номер у боті та в полі введення збігаються

**Якщо бот недоступний:**
- OTP зберігається в Redis, але не надсилається автоматично
- Зверніться до адміністратора для отримання коду

### Помилка "Redis недоступний"

```bash
# Перевірте статус Redis
redis-cli ping  # Відповідь: PONG

# Запустіть Redis якщо потрібно
sudo systemctl start redis
```

### Помилка збірки Android

```bash
# Очищення кешу Gradle
cd android
./gradlew clean

# Оновлення Capacitor
npx cap sync android
```

### Проблеми з CORS

Переконайтеся, що в `webapp/api.py` є CORS middleware з правильними origins (дивіться [розділ конфігурація](#cors-налаштування)).

---

## Внесення змін

1. Редагуйте веб-активи у `www/`
2. Запустіть `npx cap sync android` для синхронізації з Android
3. Тестуйте через `npx cap run android`

### Додавання нового Capacitor-плагіна

```bash
npm install @capacitor/plugin-name
npx cap sync android
```

---

*EpicService Android App — версія 1.0.0*  
*Сервер: https://anubis-ua.pp.ua*
