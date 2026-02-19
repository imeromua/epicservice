# Redis Caching Guide

## Overview

EpicService використовує **Redis** для кешування дорогих операцій:
- Пошук продуктів
- Статистика користувачів
- Адмін дашборд
- Каталог продуктів

---

## 🚀 Quick Start

### **1. Decorator-based Caching**

```python
from utils.cache import cached
from utils.cache_keys import CacheKeys

@cached(ttl=CacheKeys.TTL_LONG, key_prefix="products_search")
async def search_products(query: str):
    # Expensive database query
    return await db.query(...)
```

### **2. Manual Caching**

```python
from utils.cache import cache
from utils.cache_keys import CacheKeys

# Get from cache
cache_key = CacheKeys.product_search("laptop")
cached_data = await cache.get(cache_key)

if not cached_data:
    # Query database
    cached_data = await query_database()
    
    # Store in cache
    await cache.set(cache_key, cached_data, ttl=600)
```

### **3. Cache Invalidation**

```python
from utils.cache import invalidate_cache
from utils.cache_keys import CacheKeys

# Invalidate all product cache
await invalidate_cache(CacheKeys.invalidate_products())

# Invalidate user cache
await invalidate_cache(CacheKeys.invalidate_user(user_id))
```

---

## ⏱️ Cache TTLs

| Data Type | TTL | Reason |
|-----------|-----|--------|
| **Product Search** | 10 min | Catalog changes rarely |
| **User List** | 5 min | Updates frequently |
| **User Stats** | 5 min | Recalculated often |
| **Admin Dashboard** | 1 hour | Heavy queries, changes rarely |
| **Product by Article** | 10 min | Stable data |

### **TTL Constants**

```python
from utils.cache_keys import CacheKeys

CacheKeys.TTL_SHORT = 60        # 1 minute
CacheKeys.TTL_MEDIUM = 300      # 5 minutes
CacheKeys.TTL_LONG = 600        # 10 minutes
CacheKeys.TTL_VERY_LONG = 3600  # 1 hour
```

---

## 🔑 Cache Keys

### **Naming Convention**

```
{entity}:{operation}:{identifier}
```

**Examples:**
- `products:search:abc123` - Product search results
- `user:list:123456789` - User temp list
- `user:stats:123456789` - User statistics
- `admin:stats` - Admin dashboard

### **Predefined Keys**

```python
from utils.cache_keys import CacheKeys

# Products
CacheKeys.PRODUCTS_ALL
CacheKeys.product_search("query")
CacheKeys.PRODUCTS_BY_ARTICLE

# Users
CacheKeys.user_list(user_id)
CacheKeys.user_stats(user_id)

# Admin
CacheKeys.ADMIN_STATS
```

---

## 📚 Usage Examples

### **Example 1: Search with Caching**

```python
from fastapi import FastAPI
from utils.cache import cached
from utils.cache_keys import CacheKeys

@app.get("/api/search")
@cached(ttl=CacheKeys.TTL_LONG, key_prefix="search")
async def search_products(query: str):
    """Cached for 10 minutes."""
    service = ProductService(session)
    return await service.search(query)
```

### **Example 2: Cache with Invalidation**

```python
@app.post("/api/admin/import")
async def import_products(file: UploadFile):
    # Import products
    result = await process_import(file)
    
    # Invalidate product cache
    await invalidate_cache("products:*")
    
    return {"imported": result["count"]}
```

### **Example 3: Conditional Caching**

```python
@app.get("/api/stats")
async def get_stats(
    user_id: int,
    force_refresh: bool = False,
):
    cache_key = CacheKeys.user_stats(user_id)
    
    # Bypass cache if requested
    if not force_refresh:
        cached = await cache.get(cache_key)
        if cached:
            return {**cached, "cached": True}
    
    # Calculate stats
    stats = await calculate_stats(user_id)
    await cache.set(cache_key, stats, ttl=300)
    
    return {**stats, "cached": False}
```

### **Example 4: Cache Warming**

```python
@app.on_event("startup")
async def warm_cache():
    """Pre-populate cache on startup."""
    # All products
    products = await get_all_products()
    await cache.set(
        CacheKeys.PRODUCTS_ALL,
        products,
        ttl=CacheKeys.TTL_LONG,
    )
    
    logger.info("Cache warmed", keys=1)
```

---

## 📊 Monitoring

### **Cache Stats**

```python
@app.get("/api/admin/cache/stats")
async def cache_stats():
    if not cache._redis:
        return {"enabled": False}
    
    info = await cache._redis.info("stats")
    
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    total = hits + misses
    
    return {
        "enabled": True,
        "hits": hits,
        "misses": misses,
        "hit_rate": hits / total if total > 0 else 0,
    }
```

### **Cache Size**

```bash
# Redis CLI
redis-cli

> INFO memory
> DBSIZE
> KEYS products:*
```

---

## ⚠️ Best Practices

### **✅ DO**

1. **Cache expensive operations:**
   ```python
   @cached(ttl=600)  # 10 minutes
   async def expensive_aggregation():
       return await db.execute(complex_query)
   ```

2. **Invalidate on updates:**
   ```python
   await update_product(product_id, data)
   await invalidate_cache(f"products:*")
   ```

3. **Use appropriate TTLs:**
   - Frequently changing data: 1-5 min
   - Stable data: 10-60 min
   - Static data: 1+ hours

4. **Handle cache failures gracefully:**
   ```python
   cached_data = await cache.get(key)
   if cached_data is None:
       # Fallback to database
       data = await query_database()
   ```

### **❌ DON'T**

1. **Don't cache user-sensitive data without encryption**
2. **Don't use very long TTLs for frequently updated data**
3. **Don't cache large objects (>1MB)**
4. **Don't forget to invalidate on updates**

---

## 🛠️ Configuration

### **Development (Optional Redis)**

```python
# config.py
REDIS_HOST = "localhost"
REDIS_PORT = 6379

# Cache disabled if Redis unavailable
```

### **Production (Required Redis)**

```bash
# Install Redis
sudo apt install redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis

# Check status
redis-cli ping  # Should return PONG
```

### **Connection in App**

```python
from fastapi import FastAPI
from utils.cache import cache

app = FastAPI()

@app.on_event("startup")
async def startup():
    await cache.connect()

@app.on_event("shutdown")
async def shutdown():
    await cache.disconnect()
```

---

## 🐞 Troubleshooting

### **Cache not working**

```python
# Check if enabled
print(cache._enabled)  # Should be True

# Check Redis connection
await cache._redis.ping()  # Should not raise
```

### **High memory usage**

```bash
# Check memory
redis-cli INFO memory

# Clear cache
redis-cli FLUSHDB

# Or via API
await cache.clear()
```

### **Low hit rate**

- Check TTLs (may be too short)
- Check key generation (keys may not match)
- Monitor with `cache_stats()` endpoint

---

## 🔗 References

- [Redis Documentation](https://redis.io/documentation)
- [redis-py Async](https://redis-py.readthedocs.io/)
- [Caching Strategies](https://aws.amazon.com/caching/best-practices/)
