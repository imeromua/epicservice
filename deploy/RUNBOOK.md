# Production runbook

Це короткий runbook для типових продакшн-операцій: деплой, рестарт, міграції, перевірка стану, rollback.

## Передумови

- Сервер з налаштованими systemd сервісами: `epicservice.service` (бот) і `webapp.service` (API).
- Проєкт розгорнутий через git (каталог, де робиться `git pull`).

## Деплой (звичайний)

```bash
cd /home/epicservice

git pull origin main

# (опційно) активувати venv
source venv/bin/activate

pip install -r requirements.txt

alembic upgrade head

sudo systemctl restart webapp.service
sudo systemctl restart epicservice.service

sudo systemctl status webapp.service
sudo systemctl status epicservice.service
```

## Перевірка стану

```bash
curl -s http://127.0.0.1:8000/health

sudo journalctl -u webapp.service -n 50 --no-pager
sudo journalctl -u epicservice.service -n 50 --no-pager
```

## Rollback (код)

1) Визначити робочий коміт/тег (наприклад, `v2.2.0`).

```bash
cd /home/epicservice

git fetch --tags

git checkout v2.2.0

sudo systemctl restart webapp.service
sudo systemctl restart epicservice.service
```

## Rollback (міграції)

Увага: rollback міграцій роби тільки якщо точно розумієш наслідки для даних.

```bash
# приклад: відкотитись на 1 ревізію назад
alembic downgrade -1
```

## Аварійний рестарт

```bash
sudo systemctl restart webapp.service
sudo systemctl restart epicservice.service
```

---

"Зроблено в Україні з ❤️"
