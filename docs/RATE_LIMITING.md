# Rate Limiting Guide

## Overview

EpicService використовує [SlowAPI](https://github.com/laurentS/slowapi) для захисту від DoS атак та зловживань API.

---

## 🔒 Configured Limits

### **Public Endpoints**
| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/api/search` | 10/min | Resource-intensive query |
| `/health` | 60/min | Health checks |

### **User Endpoints**
| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/api/list` (GET) | 30/min | Normal usage |
| `/api/list/add` | 20/min | Prevent spam |
| `/api/list/save` | 5/min | Excel generation (heavy) |
| `/api/archives` | 20/min | Normal usage |
| `/api/archives/download` | 10/min | File download |
| `/api/statistics` | 30/min | Normal usage |

### **Admin Endpoints**
| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/api/admin/stats` | 60/min | Dashboard polling |
| `/api/admin/import` | 2/min | Excel import (very heavy) |
| `/api/admin/export` | 10/min | Report generation |
| `/api/admin/broadcast` | 1/min | Prevent spam |
| `/api/admin/force-save` | 10/min | Resource-intensive |

**Note:** Admins automatically get 3x higher limits.

---

## 📝 Usage

### **Basic Usage**

```python
from fastapi import FastAPI, Request
from middlewares import limiter, setup_rate_limiting, RateLimitConfig

app = FastAPI()
setup_rate_limiting(app)

@app.get("/api/search")
@limiter.limit(RateLimitConfig.SEARCH)  # 10/minute
async def search(request: Request, query: str):
    return {"results": [...]}
```

### **Custom Limits**

```python
@app.post("/api/expensive-operation")
@limiter.limit("2/minute")  # Custom limit
async def expensive(request: Request):
    return {"result": "done"}
```

### **Multiple Limits**

```python
@app.get("/api/data")
@limiter.limit("100/hour;10/minute")  # Both limits apply
async def get_data(request: Request):
    return {"data": [...]}
```

### **Exempt Endpoint**

```python
@app.get("/api/public")
@limiter.exempt  # No rate limiting
async def public_endpoint():
    return {"public": "data"}
```

---

## 🎯 Rate Limit Key

Rate limits are tracked by:

1. **User ID** (if present in query params)
   - Example: `/api/search?user_id=123456789&query=test`
   - Key: `user:123456789`

2. **IP Address** (fallback)
   - Example: Request from `192.168.1.1`
   - Key: `192.168.1.1`

This means:
- Authenticated users have separate limits per user
- Anonymous requests share limits per IP

---

## 🚨 Error Response

When rate limit is exceeded:

```json
{
  "success": false,
  "error": "RateLimitExceeded",
  "message": "Too many requests. Please try again later.",
  "details": {
    "retry_after": "42",
    "limit": "10 per 1 minute"
  }
}
```

**HTTP Status:** `429 Too Many Requests`

**Headers:**
- `X-RateLimit-Limit` - Total requests allowed
- `X-RateLimit-Remaining` - Requests remaining
- `X-RateLimit-Reset` - Time until reset (epoch)
- `Retry-After` - Seconds to wait

---

## 🛠️ Configuration

### **Development (In-Memory)**

```python
from slowapi import Limiter

limiter = Limiter(
    key_func=get_user_id_or_ip,
    storage_uri="memory://",  # Fast, but resets on restart
)
```

### **Production (Redis)**

```python
limiter = Limiter(
    key_func=get_user_id_or_ip,
    storage_uri="redis://localhost:6379",  # Persistent across restarts
)
```

**Benefits of Redis:**
- Shared state across multiple workers
- Persistent across restarts
- Better performance for high traffic

---

## 📊 Monitoring

### **Check Rate Limit Headers**

```bash
curl -I http://localhost:8000/api/search?query=test

X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1708372800
```

### **Test Rate Limiting**

```bash
# Send 15 requests quickly
for i in {1..15}; do
  curl http://localhost:8000/api/search?query=test
done

# After 10 requests, you'll see 429 errors
```

---

## ⚠️ Best Practices

1. **Don't over-limit** - Users should be able to use the app normally
2. **Heavy operations get low limits** - Excel import, broadcast, etc.
3. **Use Redis in production** - In-memory storage resets on restart
4. **Monitor 429 errors** - Adjust limits if users hit them too often
5. **Exempt health checks** - Monitoring shouldn't be rate-limited

---

## 📝 Adding New Endpoint

1. **Add limit to config:**

```python
# middlewares/rate_limit_config.py
class RateLimitConfig:
    MY_ENDPOINT = "15/minute"
```

2. **Apply to endpoint:**

```python
@app.get("/api/my-endpoint")
@limiter.limit(RateLimitConfig.MY_ENDPOINT)
async def my_endpoint(request: Request):
    return {"data": "..."}
```

3. **Write tests:**

```python
def test_my_endpoint_rate_limit():
    # Test that limit works
    for i in range(15):
        response = client.get("/api/my-endpoint")
        assert response.status_code == 200
    
    # 16th request fails
    response = client.get("/api/my-endpoint")
    assert response.status_code == 429
```

---

## 🔗 References

- [SlowAPI Documentation](https://github.com/laurentS/slowapi)
- [HTTP 429 Status Code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)
- [Rate Limiting Best Practices](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
