"""Example of using rate limiting in FastAPI endpoints."""

from fastapi import FastAPI, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from middlewares import limiter, setup_rate_limiting, RateLimitConfig
from schemas import ProductSearchResponse
from services import ProductService

# Create app
app = FastAPI(title="EpicService with Rate Limiting")

# Setup rate limiting
setup_rate_limiting(app)


# Example 1: Simple rate limit
@app.get("/api/health")
@limiter.limit(RateLimitConfig.HEALTH)
async def health_check(request: Request):
    """Health check with rate limiting."""
    return {"status": "ok", "service": "epicservice"}


# Example 2: Rate limit with dynamic user_id
@app.get("/api/search", response_model=ProductSearchResponse)
@limiter.limit(RateLimitConfig.SEARCH)
async def search_products(
    request: Request,  # Required for rate limiting
    query: str,
    user_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Search products with rate limiting.
    
    Rate limit: 10 requests per minute per user_id
    """
    service = ProductService(session)
    products = await service.search(query, limit=50)
    
    return ProductSearchResponse(
        products=products,
        total=len(products),
        query=query,
    )


# Example 3: Admin endpoint with higher limit
@app.post("/api/admin/broadcast")
@limiter.limit(RateLimitConfig.ADMIN_BROADCAST)
async def broadcast_message(
    request: Request,
    user_id: int,
    message: str,
):
    """
    Admin broadcast with strict rate limiting.
    
    Rate limit: 1 request per minute (prevents spam)
    """
    # Check if admin
    if user_id not in ADMIN_IDS:
        raise HTTPException(403, "Admin access required")
    
    # Send broadcast
    await send_broadcast(message)
    
    return {"success": True, "message": "Broadcast sent"}


# Example 4: Expensive operation with low limit
@app.post("/api/admin/import")
@limiter.limit(RateLimitConfig.ADMIN_IMPORT)
async def import_products(
    request: Request,
    file: UploadFile,
):
    """
    Import products from Excel.
    
    Rate limit: 2 requests per minute (expensive operation)
    """
    # Process Excel import
    result = await process_excel_import(file)
    
    return result


# Example 5: Different limits for different users
@app.get("/api/list")
async def get_user_list(
    request: Request,
    user_id: int,
):
    """
    Get user list with dynamic rate limiting.
    
    Regular users: 30/minute
    Admins: 90/minute (3x)
    """
    is_admin = user_id in ADMIN_IDS
    limit = RateLimitConfig.get_limit("list_get", is_admin=is_admin)
    
    # Apply dynamic limit
    limiter.limit(limit)(get_user_list)
    
    # Get list
    service = ListService(session)
    user_list = await service.get_list(user_id)
    
    return user_list


# Example 6: Exempt endpoint from rate limiting
@app.get("/api/public/info")
@limiter.exempt
async def public_info():
    """
    Public endpoint without rate limiting.
    
    Use sparingly - only for truly public data!
    """
    return {
        "name": "EpicService",
        "version": "3.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
