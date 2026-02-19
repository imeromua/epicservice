"""Examples of using Redis cache."""

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from utils.cache import cache, cached, invalidate_cache
from utils.cache_keys import CacheKeys
from services import ProductService

app = FastAPI()


@app.on_event("startup")
async def startup():
    """Connect to Redis on startup."""
    await cache.connect()


@app.on_event("shutdown")
async def shutdown():
    """Disconnect from Redis on shutdown."""
    await cache.disconnect()


# Example 1: Decorator-based caching
@app.get("/api/products/search")
@cached(ttl=CacheKeys.TTL_LONG, key_prefix="products_search")
async def search_products(query: str, session: AsyncSession = Depends(get_session)):
    """Search products with automatic caching (10 min TTL)."""
    service = ProductService(session)
    return await service.search(query)


# Example 2: Manual cache control
@app.get("/api/products/{article}")
async def get_product(article: str, session: AsyncSession = Depends(get_session)):
    """Get product with manual cache control."""
    cache_key = f"{CacheKeys.PRODUCTS_BY_ARTICLE}:{article}"
    
    # Try cache first
    cached_product = await cache.get(cache_key)
    if cached_product:
        return cached_product
    
    # Query database
    service = ProductService(session)
    product = await service.get_by_article(article)
    
    # Store in cache (10 min)
    if product:
        await cache.set(cache_key, product, ttl=CacheKeys.TTL_LONG)
    
    return product


# Example 3: Cache invalidation
@app.post("/api/admin/products/import")
async def import_products(file: UploadFile):
    """Import products and invalidate cache."""
    # Process import
    result = await process_import(file)
    
    # Invalidate all product cache
    await invalidate_cache(CacheKeys.invalidate_products())
    
    return {"imported": result["count"], "cache_cleared": True}


# Example 4: User-specific cache
@app.get("/api/user/list")
@cached(ttl=CacheKeys.TTL_MEDIUM, key_prefix="user_list")
async def get_user_list(
    user_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get user list with caching (5 min)."""
    service = ListService(session)
    return await service.get_list(user_id)


# Example 5: Conditional caching
@app.get("/api/statistics")
async def get_statistics(
    user_id: int,
    force_refresh: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Get statistics with optional cache bypass."""
    cache_key = CacheKeys.user_stats(user_id)
    
    # Bypass cache if force_refresh
    if not force_refresh:
        cached_stats = await cache.get(cache_key)
        if cached_stats:
            return {**cached_stats, "cached": True}
    
    # Calculate statistics
    service = ProductService(session)
    stats = await service.get_user_statistics(user_id)
    
    # Cache for 5 minutes
    await cache.set(cache_key, stats, ttl=CacheKeys.TTL_MEDIUM)
    
    return {**stats, "cached": False}


# Example 6: Admin dashboard with long cache
@app.get("/api/admin/dashboard")
@cached(ttl=CacheKeys.TTL_VERY_LONG, key_prefix="admin_dashboard")
async def admin_dashboard(session: AsyncSession = Depends(get_session)):
    """Admin dashboard with 1 hour cache."""
    # Heavy aggregation queries
    stats = await calculate_dashboard_stats(session)
    return stats


# Example 7: Cache warming
@app.post("/api/admin/cache/warm")
async def warm_cache(session: AsyncSession = Depends(get_session)):
    """Pre-populate cache with common queries."""
    service = ProductService(session)
    
    # Cache all products
    all_products = await service.get_all()
    await cache.set(
        CacheKeys.PRODUCTS_ALL,
        all_products,
        ttl=CacheKeys.TTL_LONG,
    )
    
    # Cache by department
    for dept in ["ПММ", "Сервісний відділ", "Заправка"]:
        dept_products = await service.get_by_department(dept)
        await cache.set(
            f"{CacheKeys.PRODUCTS_BY_DEPARTMENT}:{dept}",
            dept_products,
            ttl=CacheKeys.TTL_LONG,
        )
    
    return {"status": "cache_warmed", "keys": 4}


# Example 8: Cache stats
@app.get("/api/admin/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    if not cache._redis:
        return {"enabled": False}
    
    info = await cache._redis.info("stats")
    
    return {
        "enabled": cache._enabled,
        "hits": info.get("keyspace_hits", 0),
        "misses": info.get("keyspace_misses", 0),
        "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1),
    }
