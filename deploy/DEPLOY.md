# Інструкція з розгортання WebApp

## Оновлення коду

```bash
# Перейти в каталог проекту
cd /home/epicservice

# Запулити останні зміни
git pull origin main
```

## Виправлення systemd сервісу

### 1. Зупинити поточний сервіс
```bash
sudo systemctl stop webapp.service
```

### 2. Оновити конфігурацію сервісу
```bash
# Копіювати нову конфігурацію
sudo cp /home/epicservice/deploy/webapp.service /etc/systemd/system/webapp.service

# Перезавантажити systemd
sudo systemctl daemon-reload
```

### 3. Перевірити конфігурацію (опціонально)
```bash
# Подивитись на конфігурацію
sudo systemctl cat webapp.service
```

### 4. Запустити сервіс
```bash
sudo systemctl start webapp.service
```

### 5. Перевірити статус
```bash
sudo systemctl status webapp.service
```

### 6. Подивитись логи
```bash
# Останні 50 рядків
sudo journalctl -u webapp.service -n 50 --no-pager

# Слідкувати за логами в реальному часі
sudo journalctl -u webapp.service -f
```

## Перевірка роботи

```bash
# Health check
curl http://localhost:8000/health

# Повинно повернути:
# {"status":"ok","service":"epicservice","version":"2.0.0"}
```

## Пошук проблем

### Проблема: ImportError
```bash
# Перевірити встановлені бібліотеки
source /home/epicservice/venv/bin/activate
pip list | grep -E "fastapi|uvicorn|aiogram"

# Якщо чогось не вистачає:
pip install -r requirements.txt
```

### Проблема: Порт вже зайнятий
```bash
# Знайти процес на порту 8000
sudo lsof -i :8000

# Зупинити процес (якщо потрібно)
sudo kill -9 <PID>
```

### Проблема: Права доступу
```bash
# Перевірити власника файлів
ls -la /home/epicservice/

# Виправити права (якщо потрібно)
sudo chown -R www-data:www-data /home/epicservice/
```

## Ручний запуск (для тестування)

```bash
cd /home/epicservice
source venv/bin/activate
python -m webapp.api

# Або через uvicorn
uvicorn webapp.api:app --host 0.0.0.0 --port 8000 --reload
```

## Корисні команди

```bash
# Перезапустити сервіс
sudo systemctl restart webapp.service

# Вимкнути автозапуск
sudo systemctl disable webapp.service

# Увімкнути автозапуск
sudo systemctl enable webapp.service

# Подивитись всі логи з початку дня
sudo journalctl -u webapp.service --since today --no-pager
```

## Очікуваний результат

Після запуску в логах має бути:

```
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

А при перевірці health:
```bash
$ curl http://localhost:8000/health
{"status":"ok","service":"epicservice","version":"2.0.0"}
```
