# Local development (Docker)

Цей проєкт можна підняти локально “однією командою” через Docker Compose.

## Передумови

- Docker + Docker Compose v2
- Файл `.env` у корені (можна взяти за основу `.env.example`)

## Запуск

```bash
make up
```

Після запуску:
- WebApp буде доступний на http://localhost:8000
- Swagger: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## Корисні команди

```bash
make logs
make ps
make migrate
make restart
make down
```

## Примітки

- Міграції виконуються командою `alembic upgrade head` у сервісі `migrate`.
- Для dev-режиму використовується `--reload` у `webapp`.

---

"Зроблено в Україні з ❤️"
