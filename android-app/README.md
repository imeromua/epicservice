# 📱 EpicService — Автономний Android Додаток

Автономний Android додаток для складського обліку EpicService.
Працює без Telegram, з авторизацією за логіном та паролем, біометрією, та підтримкою офлайн-режиму.

## 🏗️ Архітектура

```
┌─────────────────────────────────────────┐
│            Android App (Kotlin)          │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ Login Screen │  │ Biometric Auth   │  │
│  │ (native)     │  │ (AndroidX)       │  │
│  └──────┬───────┘  └──────┬──────────┘  │
│         └────────┬─────────┘            │
│         ┌────────▼──────────┐           │
│         │  WebView + Bridge  │           │
│         │  (standalone.html) │           │
│         └────────┬──────────┘           │
└──────────────────┼──────────────────────┘
                   │ HTTPS
┌──────────────────▼──────────────────────┐
│          Backend (FastAPI)                │
│  ┌──────────────┐  ┌─────────────────┐  │
│  │ /api/auth/*   │  │ /api/* (client) │  │
│  │ JWT tokens    │  │ search, lists   │  │
│  └──────────────┘  └─────────────────┘  │
│  ┌──────────────────────────────────┐   │
│  │        PostgreSQL + Redis         │   │
│  └──────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

## 📋 Вимоги

### Для збірки APK:
- **Android Studio** Hedgehog (2023.1.1) або новіше
- **JDK 17** (вбудований в Android Studio)
- **Android SDK 34** (API Level 34)
- **Kotlin 1.9.22+**
- **Gradle 8.5+**

### Для серверної частини:
- Python 3.11+
- PostgreSQL 14+
- Redis 7+ (опціонально)
- Все, що вже налаштовано для основного проекту

## 🚀 Швидкий старт

### 1. Налаштування серверної частини

Серверна частина вже містить всі необхідні ендпоїнти. Необхідно:

```bash
# 1. Додати змінну JWT_SECRET_KEY в .env
echo 'JWT_SECRET_KEY=your-secure-random-secret-key-here' >> .env

# 2. Виконати міграцію бази даних
make migrate
# або напряму:
alembic upgrade head

# 3. Запустити сервер
make up
```

Нові ендпоїнти автентифікації:
- `POST /api/auth/register` — реєстрація (login, password, first_name)
- `POST /api/auth/login` — авторизація (login, password)
- `POST /api/auth/refresh` — оновлення access токена
- `GET /api/auth/me` — інформація про поточного користувача
- `GET /standalone` — сторінка автономного додатку

### 2. Збірка Android APK

#### Спосіб 1: Android Studio (рекомендовано)

```bash
# 1. Відкрийте Android Studio
# 2. File → Open → виберіть папку android-app/
# 3. Дочекайтесь синхронізації Gradle
# 4. Налаштуйте URL сервера (див. нижче)
# 5. Build → Build Bundle(s) / APK(s) → Build APK(s)
```

#### Спосіб 2: Командний рядок (Gradle)

```bash
cd android-app/

# Налаштуйте URL сервера
echo 'SERVER_URL=https://your-server.com' >> local.properties

# Debug APK (для тестування)
./gradlew assembleDebug

# Release APK (для продакшену)
./gradlew assembleRelease

# APK файл буде в:
# Debug:   app/build/outputs/apk/debug/app-debug.apk
# Release: app/build/outputs/apk/release/app-release-unsigned.apk
```

### 3. Налаштування URL сервера

У файлі `android-app/app/build.gradle.kts` замініть URL сервера:

```kotlin
defaultConfig {
    // Замініть на адресу вашого сервера
    buildConfigField("String", "SERVER_URL", "\"https://your-server.com\"")
}
```

Або створіть `android-app/local.properties`:
```properties
SERVER_URL=https://your-server.com
```

### 4. Підписання Release APK

Для публікації в Google Play або встановлення на пристрій:

```bash
# 1. Створіть keystore (один раз)
keytool -genkey -v -keystore epicservice.keystore \
  -alias epicservice -keyalg RSA -keysize 2048 -validity 10000

# 2. Додайте до local.properties
echo 'KEYSTORE_FILE=../epicservice.keystore' >> local.properties
echo 'KEYSTORE_PASSWORD=your-keystore-password' >> local.properties
echo 'KEY_ALIAS=epicservice' >> local.properties
echo 'KEY_PASSWORD=your-key-password' >> local.properties

# 3. Зберіть підписаний APK
./gradlew assembleRelease
```

## 📱 Функціонал додатку

### Автентифікація
- ✅ Реєстрація за логіном та паролем
- ✅ Авторизація з JWT токенами
- ✅ Автоматичне оновлення токенів
- ✅ Біометрична автентифікація (відбиток пальця / Face ID)
- ✅ Безпечне зберігання сесії

### Основний функціонал (як у Mini App)
- ✅ Пошук товарів (нечіткий пошук)
- ✅ Управління списком замовлень
- ✅ Архіви збережених списків
- ✅ Фільтри по відділах та групах
- ✅ Фото товарів (завантаження та перегляд)
- ✅ Модерація фото (для модераторів)
- ✅ Адмін-панель (імпорт, статистика, розсилки)

### Офлайн-режим
- ✅ Кешування статичних ресурсів (Service Worker)
- ✅ Збереження сесії в localStorage
- ✅ Кешування API відповідей
- ✅ Автоматична синхронізація при відновленні з'єднання

### Android-специфічні функції
- ✅ Нативна вібрація замість Telegram Haptic Feedback
- ✅ Свайп для оновлення (Pull-to-Refresh)
- ✅ Нативний файловий менеджер для завантаження
- ✅ Підтримка темної теми
- ✅ Адаптивний інтерфейс

## 🔐 Безпека

- JWT токени з обмеженим терміном дії (24 години access, 30 днів refresh)
- Хешування паролів bcrypt
- HTTPS для всіх з'єднань (у production)
- Cleartext дозволений тільки для localhost (розробка)
- Біометрична автентифікація через AndroidX Biometric API

## 🧪 Тестування

### Backend тести
```bash
# Запуск тестів автентифікації
python -m pytest tests/test_auth.py -v

# Запуск всіх тестів
python -m pytest tests/ -v
```

### Ручне тестування

1. Запустіть сервер: `make up`
2. Відкрийте `http://localhost:8000/standalone` у браузері
3. Зареєструйтесь та перевірте функціонал
4. Встановіть APK на Android пристрій та повторіть перевірку

## 📁 Структура файлів

```
android-app/                          # Android проект
├── app/
│   ├── build.gradle.kts              # Залежності та конфігурація
│   ├── proguard-rules.pro            # ProGuard правила
│   └── src/main/
│       ├── AndroidManifest.xml       # Маніфест додатку
│       ├── java/com/epicservice/app/
│       │   ├── EpicServiceApp.kt     # Application клас
│       │   ├── MainActivity.kt       # Головна активність (WebView)
│       │   └── AndroidBridge.kt      # JS ↔ Native міст
│       └── res/
│           ├── layout/               # XML layouts
│           ├── values/               # Кольори, рядки, теми
│           └── xml/                  # Network security config
├── build.gradle.kts                  # Кореневий Gradle
├── settings.gradle.kts               # Налаштування проекту
└── gradle/                           # Gradle wrapper

webapp/
├── routers/
│   └── auth.py                       # JWT автентифікація (НОВИЙ)
├── templates/
│   └── standalone.html               # Автономна сторінка (НОВИЙ)
└── static/standalone/
    ├── auth.js                       # Клієнтська автентифікація
    ├── standalone-utils.js           # Utils без Telegram
    ├── sw-standalone.js              # Service Worker для офлайн
    ├── manifest.json                 # PWA маніфест
    └── login.css                     # Стилі логін-форми

database/
└── models.py                         # + login, password_hash поля

alembic/versions/
└── d1a2b3c4d5e6_add_standalone_auth_fields.py  # Міграція

tests/
└── test_auth.py                      # 15 тестів автентифікації (НОВИЙ)
```

## ⚠️ Важливі замітки

1. **JWT_SECRET_KEY** — обов'язково змініть на випадкове значення у production!
2. **SERVER_URL** — вкажіть реальну адресу сервера перед збіркою APK
3. **HTTPS** — у production використовуйте тільки HTTPS
4. **Keystore** — зберігайте keystore файл у безпечному місці, не додавайте до Git
