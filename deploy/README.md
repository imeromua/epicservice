# Deployment Guide

## 🚀 Production Deployment

### **Prerequisites**

- Ubuntu 22.04 LTS or newer
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Nginx
- Systemd

---

## 💻 Installation Steps

### **1. Create User**

```bash
sudo useradd -m -s /bin/bash epicservice
sudo mkdir -p /opt/epicservice
sudo chown epicservice:epicservice /opt/epicservice
```

### **2. Clone Repository**

```bash
sudo -u epicservice git clone https://github.com/imeromua/epicservice.git /opt/epicservice
cd /opt/epicservice
sudo -u epicservice git checkout main  # or 3.0.0-beta
```

### **3. Create Virtual Environment**

```bash
sudo -u epicservice python3.11 -m venv /opt/epicservice/venv
sudo -u epicservice /opt/epicservice/venv/bin/pip install --upgrade pip
sudo -u epicservice /opt/epicservice/venv/bin/pip install -r requirements.txt
```

### **4. Configure Environment**

```bash
sudo -u epicservice cp .env.example /opt/epicservice/.env
sudo -u epicservice nano /opt/epicservice/.env
```

**Required variables:**
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=epicservice
DB_PASSWORD=<strong-password>
DB_NAME=epicservice

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Telegram
BOT_TOKEN=<your-bot-token>
ADMIN_IDS=123456789,987654321

# WebApp
WEBAPP_URL=https://your-domain.com
```

### **5. Setup Database**

```bash
sudo -u postgres createuser epicservice
sudo -u postgres createdb -O epicservice epicservice
sudo -u postgres psql -c "ALTER USER epicservice WITH PASSWORD '<password>';"

# Run migrations
sudo -u epicservice /opt/epicservice/venv/bin/alembic upgrade head
```

### **6. Create Log Directories**

```bash
sudo mkdir -p /var/log/epicservice
sudo mkdir -p /var/run/epicservice
sudo chown epicservice:epicservice /var/log/epicservice
sudo chown epicservice:epicservice /var/run/epicservice
```

### **7. Install Systemd Service**

```bash
sudo cp /opt/epicservice/deploy/epicservice.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable epicservice
```

### **8. Configure Nginx**

```bash
sudo cp /opt/epicservice/deploy/nginx.conf /etc/nginx/sites-available/epicservice
sudo ln -s /etc/nginx/sites-available/epicservice /etc/nginx/sites-enabled/

# Edit domain name
sudo nano /etc/nginx/sites-available/epicservice

# Test config
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

### **9. SSL Certificate (Let's Encrypt)**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### **10. Start Service**

```bash
sudo systemctl start epicservice
sudo systemctl status epicservice
```

---

## 🔍 Monitoring

### **Check Logs**

```bash
# Service logs
sudo journalctl -u epicservice -f

# Application logs
tail -f /var/log/epicservice/error.log
tail -f /var/log/epicservice/access.log

# Nginx logs
tail -f /var/log/nginx/epicservice_error.log
```

### **Check Status**

```bash
# Service status
sudo systemctl status epicservice

# Worker processes
ps aux | grep gunicorn

# Connections
sudo netstat -tlnp | grep :8000
```

---

## 🔄 Updates

### **Pull Latest Code**

```bash
cd /opt/epicservice
sudo -u epicservice git pull
sudo -u epicservice /opt/epicservice/venv/bin/pip install -r requirements.txt
sudo -u epicservice /opt/epicservice/venv/bin/alembic upgrade head
```

### **Restart Service**

```bash
# Graceful reload (no downtime)
sudo systemctl reload epicservice

# Full restart
sudo systemctl restart epicservice
```

---

## ⚙️ Configuration

### **Workers**

Edit `/opt/epicservice/deploy/gunicorn.conf.py`:

```python
# Auto-calculate based on CPU cores
workers = multiprocessing.cpu_count() * 2 + 1

# Or set manually
workers = 4
```

### **Timeout**

```python
# Request timeout
timeout = 30

# Graceful shutdown timeout
graceful_timeout = 30
```

### **Memory Management**

```python
# Restart worker after N requests (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 50
```

---

## 🐞 Troubleshooting

### **Service won't start**

```bash
# Check logs
sudo journalctl -u epicservice -n 50 --no-pager

# Check permissions
ls -la /opt/epicservice
ls -la /var/log/epicservice
ls -la /var/run/epicservice

# Check Python path
sudo -u epicservice /opt/epicservice/venv/bin/python --version
```

### **Database connection failed**

```bash
# Test connection
sudo -u epicservice psql -h localhost -U epicservice -d epicservice

# Check PostgreSQL status
sudo systemctl status postgresql
```

### **Redis connection failed**

```bash
# Test connection
redis-cli ping

# Check Redis status
sudo systemctl status redis
```

### **502 Bad Gateway**

```bash
# Check if app is running
sudo systemctl status epicservice

# Check if port is listening
sudo netstat -tlnp | grep :8000

# Check Nginx error log
sudo tail -f /var/log/nginx/epicservice_error.log
```

---

## 📊 Performance Tuning

### **Database**

```sql
-- Add indexes
CREATE INDEX idx_products_article ON products(article);
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_temp_lists_user ON temp_lists(telegram_id);
```

### **Redis Cache**

Enable cache warming:

```bash
curl -X POST https://your-domain.com/api/admin/cache/warm
```

### **System Limits**

Edit `/etc/security/limits.conf`:

```
epicservice soft nofile 65535
epicservice hard nofile 65535
```

---

## 🔒 Security

### **Firewall**

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### **Fail2ban**

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### **Auto-updates**

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## 📝 Backup

### **Database Backup**

```bash
# Manual backup
sudo -u postgres pg_dump epicservice > epicservice_$(date +%Y%m%d).sql

# Automated daily backup (crontab)
0 2 * * * sudo -u postgres pg_dump epicservice | gzip > /backups/epicservice_$(date +\%Y\%m\%d).sql.gz
```

### **Files Backup**

```bash
tar -czf epicservice_backup_$(date +%Y%m%d).tar.gz \
    /opt/epicservice/.env \
    /opt/epicservice/archives/ \
    /var/log/epicservice/
```
