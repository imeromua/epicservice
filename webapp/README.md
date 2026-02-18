# EpicService Web App

Telegram Mini App для роботи з EpicService ботом.

## Функціонал

- 🔍 **Пошук товарів** в реальному часі
- 🛒 **Додавання в список** з вибором кількості
- 📋 **Перегляд поточного списку**
- 💰 **Підрахунок суми** автоматично

## Запуск

### 1. Оновити systemd service

```bash
sudo nano /etc/systemd/system/webapp.service
```

Замінити на:

```ini
[Unit]
Description=EpicService WebApp
After=network.target

[Service]
User=anubis
WorkingDirectory=/home/anubis/epicservice/webapp
Environment="PATH=/home/anubis/epicservice/venv/bin"
ExecStart=/home/anubis/epicservice/venv/bin/python api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Перезапустити сервіс

```bash
cd /home/anubis/epicservice
git pull

sudo systemctl daemon-reload
sudo systemctl restart webapp
sudo systemctl restart epicservice
sudo systemctl status webapp
```

### 3. Перевірити

Відкрийте у браузері:
- https://anubis-ua.pp.ua

Або в Telegram боті:
1. `/start`
2. Натисніть **🚀 Веб-додаток**
3. **🚀 Відкрити додаток**

## API Endpoints

### POST /api/search
Пошук товарів

```json
{
  "query": "артикул",
  "user_id": 123456
}
```

### GET /api/list/{user_id}
Отримати список користувача

### POST /api/add
Додати товар до списку

```json
{
  "user_id": 123456,
  "product_id": 789,
  "quantity": 5
}
```

## Структура

```
webapp/
├── api.py              # FastAPI додаток
├── templates/
│   └── index.html      # Основний інтерфейс
└── static/           # Статичні файли
```

## Логи

```bash
# Логи webapp
sudo journalctl -u webapp -f

# Логи бота
sudo journalctl -u epicservice -f
```
