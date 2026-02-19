"""Cache key patterns for different entities."""


class CacheKeys:
    """Cache key patterns and TTLs."""

    # Product catalog
    PRODUCTS_ALL = "products:all"
    PRODUCTS_SEARCH = "products:search"  # + query hash
    PRODUCTS_BY_ARTICLE = "products:article"  # + article
    PRODUCTS_BY_DEPARTMENT = "products:dept"  # + department

    # User data
    USER_LIST = "user:list"  # + user_id
    USER_STATS = "user:stats"  # + user_id
    USER_ARCHIVES = "user:archives"  # + user_id

    # Admin dashboard
    ADMIN_STATS = "admin:stats"
    ADMIN_DEPARTMENT_STATS = "admin:dept_stats"  # + department

    # TTLs (in seconds)
    TTL_SHORT = 60  # 1 minute
    TTL_MEDIUM = 300  # 5 minutes
    TTL_LONG = 600  # 10 minutes
    TTL_VERY_LONG = 3600  # 1 hour

    @staticmethod
    def product_search(query: str) -> str:
        """Generate cache key for product search."""
        import hashlib
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"{CacheKeys.PRODUCTS_SEARCH}:{query_hash}"

    @staticmethod
    def user_list(user_id: int) -> str:
        """Generate cache key for user list."""
        return f"{CacheKeys.USER_LIST}:{user_id}"

    @staticmethod
    def user_stats(user_id: int) -> str:
        """Generate cache key for user statistics."""
        return f"{CacheKeys.USER_STATS}:{user_id}"

    @staticmethod
    def invalidate_user(user_id: int) -> str:
        """Pattern to invalidate all user cache."""
        return f"user:*:{user_id}"

    @staticmethod
    def invalidate_products() -> str:
        """Pattern to invalidate all product cache."""
        return "products:*"
