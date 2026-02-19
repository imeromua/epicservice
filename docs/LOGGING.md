# Structured Logging Guide

## Overview

EpicService використовує **structured JSON logging** з підтримкою **correlation ID** для легкого трейсингу запитів.

---

## 📝 Log Format

### **JSON Structure**

```json
{
  "timestamp": "2026-02-19T19:52:00.123456Z",
  "level": "INFO",
  "logger": "epicservice.api",
  "message": "User search completed",
  "correlation_id": "abc-123-def-456",
  "extra": {
    "user_id": 123456789,
    "query": "test",
    "duration_ms": 45.2
  },
  "source": {
    "file": "/app/webapp/api.py",
    "line": 123,
    "function": "search_products"
  }
}
```

### **Fields**

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 UTC timestamp |
| `level` | string | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `logger` | string | Logger name (e.g., epicservice.api) |
| `message` | string | Log message |
| `correlation_id` | string | Request correlation ID (UUID) |
| `extra` | object | Custom fields |
| `source` | object | Source code location |
| `exception` | string | Exception traceback (if error) |

---

## 🛠️ Available Loggers

```python
from utils.logger import logger, api_logger, bot_logger, db_logger

# General purpose
logger.info("Application started")

# API layer
api_logger.info("Request processed")

# Bot layer
bot_logger.info("Message sent")

# Database layer
db_logger.info("Query executed")
```

---

## 🔗 Correlation ID

### **What is Correlation ID?**

Unique identifier that tracks a request through the entire system:
- FastAPI → Service → Repository → Database
- Allows filtering logs for a single request
- Helps debug issues across multiple components

### **How it works**

1. **Client sends header:**
   ```bash
   curl -H "X-Correlation-ID: my-request-123" http://localhost:8000/api/search
   ```

2. **Auto-generated if missing:**
   - Middleware generates UUID if no header
   - Example: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

3. **Propagated everywhere:**
   - All logs within that request have same correlation_id
   - Returned in response header `X-Correlation-ID`

### **Filtering logs by correlation ID**

```bash
# View all logs for specific request
cat app.log | grep '"correlation_id": "abc-123"'

# With jq
cat app.log | jq 'select(.correlation_id == "abc-123")'
```

---

## 📚 Usage Examples

### **1. Basic Logging**

```python
from utils.logger import logger

logger.info("Application started")
logger.debug("Debug information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical issue!")
```

### **2. Logging with Context**

```python
api_logger.info(
    "User search",
    user_id=123456789,
    query="laptop",
    results_count=15,
    duration_ms=42.5,
)
```

**Output:**
```json
{
  "message": "User search",
  "extra": {
    "user_id": 123456789,
    "query": "laptop",
    "results_count": 15,
    "duration_ms": 42.5
  }
}
```

### **3. Exception Logging**

```python
try:
    result = risky_operation()
except Exception as exc:
    logger.exception(
        "Operation failed",
        operation="risky_operation",
        input_data=data,
    )
    raise
```

**Output includes full traceback:**
```json
{
  "level": "ERROR",
  "message": "Operation failed",
  "exception": "Traceback (most recent call last):\n...",
  "extra": {
    "operation": "risky_operation"
  }
}
```

### **4. Manual Correlation ID**

```python
from utils.logger import set_correlation_id

set_correlation_id("custom-request-id")
logger.info("Processing with custom ID")
```

---

## 📊 Best Practices

### **✅ DO**

1. **Use structured fields:**
   ```python
   # Good
   logger.info("User login", user_id=123, ip="192.168.1.1")
   
   # Bad
   logger.info(f"User {user_id} logged in from {ip}")
   ```

2. **Log at appropriate level:**
   - `DEBUG` - Detailed diagnostic info
   - `INFO` - General informational messages
   - `WARNING` - Warning but not error
   - `ERROR` - Error that needs attention
   - `CRITICAL` - Critical issue requiring immediate action

3. **Include context:**
   ```python
   api_logger.error(
       "Failed to save list",
       user_id=user_id,
       list_size=len(items),
       error=str(exc),
   )
   ```

4. **Log timing for slow operations:**
   ```python
   start = time.time()
   result = expensive_operation()
   duration = time.time() - start
   
   logger.info(
       "Operation completed",
       operation="expensive_operation",
       duration_ms=round(duration * 1000, 2),
   )
   ```

### **❌ DON'T**

1. **Don't log sensitive data:**
   ```python
   # Bad
   logger.info("User", password=user.password)  # ❌
   logger.info("Payment", card_number=card)     # ❌
   ```

2. **Don't use string formatting:**
   ```python
   # Bad
   logger.info(f"User {user_id} did {action}")  # ❌
   
   # Good
   logger.info("User action", user_id=user_id, action=action)  # ✅
   ```

3. **Don't log inside tight loops:**
   ```python
   # Bad
   for item in large_list:  # 10000 items
       logger.debug(f"Processing {item}")  # ❌
   
   # Good
   logger.info("Processing batch", batch_size=len(large_list))  # ✅
   ```

---

## 🔍 Log Analysis

### **With jq**

```bash
# Filter by level
cat app.log | jq 'select(.level == "ERROR")'

# Filter by logger
cat app.log | jq 'select(.logger | startswith("epicservice.api"))'

# Filter by user_id
cat app.log | jq 'select(.extra.user_id == 123456789)'

# Get average duration
cat app.log | jq -s 'map(.extra.duration_ms) | add / length'

# Count errors by type
cat app.log | jq -s 'group_by(.extra.error) | map({error: .[0].extra.error, count: length})'
```

### **With grep**

```bash
# Find all errors
grep '"level": "ERROR"' app.log

# Find by correlation ID
grep '"correlation_id": "abc-123"' app.log

# Find slow requests (>1000ms)
grep '"duration_ms": [0-9]\{4,\}' app.log
```

---

## 🚀 Production Setup

### **1. Log Aggregation**

Send logs to centralized system:
- **ELK Stack** (Elasticsearch + Logstash + Kibana)
- **Grafana Loki**
- **Datadog**
- **CloudWatch Logs**

### **2. Log Rotation**

```bash
# /etc/logrotate.d/epicservice
/var/log/epicservice/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 epicservice epicservice
    sharedscripts
    postrotate
        systemctl reload epicservice
    endscript
}
```

### **3. Monitoring Alerts**

Set up alerts for:
- Error rate > 5% in 5 minutes
- Critical logs
- Slow requests (p95 > 1000ms)

---

## 🔗 References

- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Structured Logging](https://www.structlog.org/en/stable/)
- [Correlation ID Pattern](https://hilton.org.uk/blog/microservices-correlation-id)
