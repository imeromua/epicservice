# 🚀 EpicService 3.0.0-beta Development

**Ця гілка містить експериментальні покращення для версії 3.0.0**

---

## 🎯 Мета релізу 3.0.0

### **Основні напрямки:**

#### 1️⃣ **Архітектура**
- ✅ Services шар (бізнес-логіка)
- ✅ DTO/Schemas (Pydantic models)
- ✅ Чітке розділення: API → Services → Repositories

#### 2️⃣ **Тести**
- ✅ pytest + pytest-asyncio
- ✅ Coverage 60%+
- ✅ Інтеграційні тести API
- ✅ Юніт-тести бізнес-логіки

#### 3️⃣ **CI/CD**
- ✅ GitHub Actions (lint + test + build)
- ✅ Pre-commit hooks
- ✅ CodeQL security analysis
- ✅ Codecov integration

#### 4️⃣ **Безпека**
- ⏳ Rate limiting (SlowAPI)
- ⏳ Enhanced logging (structured)
- ⏳ Secrets management

#### 5️⃣ **Продуктивність**
- ⏳ Gunicorn + Uvicorn workers
- ⏳ Redis cache layer
- ⏳ Optimized queries

---

## 📦 Встановлення (Dev Mode)

### **1. Клонування гілки:**
```bash
git clone https://github.com/imeromua/epicservice.git
cd epicservice
git checkout 3.0.0-beta
```

### **2. Віртуальне оточення:**
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows
```

### **3. Встановлення залежностей:**
```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt
```

### **4. Pre-commit hooks:**
```bash
pre-commit install
```

### **5. Налаштування .env:**
```bash
cp .env.example .env
nano .env  # Вкажіть реальні значення
```

---

## 🧪 Запуск тестів

### **Всі тести:**
```bash
pytest
```

### **З coverage:**
```bash
pytest --cov=. --cov-report=html
```

### **Конкретний файл:**
```bash
pytest tests/test_database/test_models.py -v
```

### **З логами:**
```bash
pytest -v -s
```

### **HTML звіт:**
```bash
pytest --cov=. --cov-report=html
# Відкрийте htmlcov/index.html в браузері
```

---

## 🎨 Код-якість

### **Форматування:**
```bash
# Black
black .

# isort
isort .

# Ruff (lint + fix)
ruff check --fix .
```

### **Перевірка (без змін):**
```bash
black --check .
isort --check-only .
ruff check .
```

### **Pre-commit (всі хуки):**
```bash
pre-commit run --all-files
```

---

## 🏗️ Структура проекту (нова)

```
epicservice/
├── services/              # 🆕 Бізнес-логіка
│   ├── __init__.py
│   ├── list_service.py
│   ├── product_service.py
│   ├── archive_service.py
│   └── admin_service.py
│
├── schemas/               # 🆕 Pydantic DTO
│   ├── __init__.py
│   ├── product.py
│   ├── list.py
│   ├── archive.py
│   └── admin.py
│
├── repositories/          # 🆕 Data Access Layer
│   ├── __init__.py
│   ├── product_repo.py
│   ├── list_repo.py
│   └── user_repo.py
│
├── tests/                 # 🆕 Тести
│   ├── conftest.py
│   ├── test_database/
│   ├── test_api/
│   ├── test_services/
│   └── test_integration/
│
├── .github/
│   └── workflows/         # 🆕 CI/CD
│       ├── ci.yml
│       └── codeql.yml
│
├── database/              # ♻️ Існуючий код
│   ├── models.py
│   ├── engine.py
│   └── orm.py            # Поступово мігруємо в repositories/
│
├── webapp/
│   ├── api.py
│   └── routers/
│       ├── client.py      # ♻️ Рефакторинг: використовує services/
│       └── admin.py       # ♻️ Рефакторинг: використовує services/
│
├── .pre-commit-config.yaml  # 🆕
├── pyproject.toml           # 🆕
├── pytest.ini               # 🆕
├── requirements-dev.txt     # 🆕
└── README_BETA.md           # 🆕 Цей файл
```

---

## 🔄 Workflow розробки

### **1. Створення нової фічі:**
```bash
# Оновити гілку
git pull origin 3.0.0-beta

# Створити feature branch
git checkout -b feature/your-feature-name
```

### **2. Розробка:**
```bash
# Код → Тести → Commit

# Форматування
black .
isort .

# Перевірка
pytest
ruff check .

# Commit
git add .
git commit -m "feat: your feature description"
```

### **3. Push:**
```bash
git push origin feature/your-feature-name
```

### **4. Pull Request:**
- Створити PR в `3.0.0-beta`
- GitHub Actions автоматично запустить CI
- Після проходження тестів → мердж

---

## 📝 Commit Convention

Використовуємо [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: добавити нову фічу
fix: виправити баг
test: додати/змінити тести
refactor: рефакторинг коду
docs: оновити документацію
ci: зміни в CI/CD
chore: інші зміни (залежності, конфіг)
```

**Приклади:**
```bash
git commit -m "feat(services): add ListService with business logic"
git commit -m "test(api): add integration tests for search endpoint"
git commit -m "refactor(database): migrate ORM queries to repositories"
git commit -m "ci: add codecov integration"
```

---

## 🐛 Відомі проблеми

### **1. SQLite in-memory для тестів**
⚠️ SQLite не підтримує всі PostgreSQL features (наприклад, `FOR UPDATE`).

**Рішення:** Для критичних тестів використовувати тестовий PostgreSQL (GitHub Actions має).

### **2. Redis в тестах**
⚠️ Деякі тести потребують справжнього Redis.

**Рішення:** Використовувати `fakeredis` або Docker контейнер.

---

## 📊 Coverage Target

**Мінімальні цілі:**
- 📦 **Services:** 80%+
- 🗄️ **Repositories:** 70%+
- 🌐 **API:** 60%+
- 📊 **Overall:** 60%+

**Поточний стан:**
```bash
pytest --cov=. --cov-report=term
```

---

## 🚀 Roadmap 3.0.0

### **Milestone 1: Тести та CI** ✅ (завершено)
- [x] pytest infrastructure
- [x] Basic unit tests
- [x] GitHub Actions CI
- [x] Pre-commit hooks
- [x] CodeQL security

### **Milestone 2: Архітектура** (в розробці)
- [ ] Services шар
- [ ] DTO/Schemas
- [ ] Repositories pattern
- [ ] Refactor API handlers

### **Milestone 3: Безпека та продуктивність**
- [ ] Rate limiting
- [ ] Structured logging
- [ ] Redis cache layer
- [ ] Gunicorn setup

### **Milestone 4: Production-ready**
- [ ] Load testing
- [ ] Security audit
- [ ] Performance optimization
- [ ] Merge to `main` → Release 3.0.0 🎉

---

## 📞 Підтримка

**Питання по 3.0.0-beta:**
- 📧 Email: imerom25@gmail.com
- 💬 Telegram: @my_life_ukr
- 🐙 GitHub Issues: [epicservice/issues](https://github.com/imeromua/epicservice/issues)

**При створенні issue вказуйте:**
- Branch: `3.0.0-beta`
- Python version
- Помилка/лог

---

## 🔗 Корисні посилання

- [Main Branch (2.0.0)](https://github.com/imeromua/epicservice/tree/main)
- [CHANGELOG](CHANGELOG.md)
- [TECHNICAL_GUIDE](TECHNICAL_GUIDE.md)
- [GitHub Actions](https://github.com/imeromua/epicservice/actions)
- [Codecov Dashboard](https://codecov.io/gh/imeromua/epicservice)

---

**Happy Coding! 🚀✨**
