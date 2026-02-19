"""Examples of using structured logging."""

from fastapi import FastAPI, HTTPException
from utils.logger import logger, api_logger, bot_logger, db_logger, set_correlation_id
from middlewares.logging_middleware import setup_logging

# Create app
app = FastAPI()

# Setup logging middleware
setup_logging(app)


# Example 1: Basic logging
@app.get("/api/example1")
async def example1():
    """Basic info logging."""
    logger.info("Processing request")
    return {"status": "ok"}


# Example 2: Logging with extra context
@app.get("/api/example2")
async def example2(user_id: int, query: str):
    """Logging with extra fields."""
    api_logger.info(
        "User search",
        user_id=user_id,
        query=query,
        action="search",
    )
    return {"results": []}


# Example 3: Error logging
@app.get("/api/example3")
async def example3(user_id: int):
    """Error logging with context."""
    try:
        # Simulate error
        if user_id < 0:
            raise ValueError("Invalid user_id")
        
        return {"user_id": user_id}
    
    except ValueError as e:
        api_logger.error(
            "Validation error",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(400, str(e))


# Example 4: Exception logging with traceback
@app.get("/api/example4")
async def example4():
    """Exception logging."""
    try:
        result = 1 / 0
        return {"result": result}
    
    except Exception as exc:
        api_logger.exception(
            "Unexpected error occurred",
            endpoint="/api/example4",
        )
        raise HTTPException(500, "Internal server error")


# Example 5: Different logger instances
@app.get("/api/example5")
async def example5():
    """Using different loggers."""
    # API layer
    api_logger.info("API request received")
    
    # Database layer
    db_logger.info("Querying database", query="SELECT * FROM products")
    
    # Bot layer
    bot_logger.info("Bot notification sent", user_id=123)
    
    return {"status": "ok"}


# Example 6: Manual correlation ID
@app.get("/api/example6")
async def example6(request_id: str):
    """Manually set correlation ID."""
    # Override auto-generated correlation ID
    set_correlation_id(f"custom-{request_id}")
    
    logger.info("Processing with custom correlation ID")
    
    return {"request_id": request_id}


# Example 7: Warning and critical logs
@app.get("/api/example7")
async def example7(threshold: int):
    """Different log levels."""
    if threshold > 90:
        logger.critical(
            "Critical threshold exceeded!",
            threshold=threshold,
            max_allowed=90,
        )
    elif threshold > 75:
        logger.warning(
            "High threshold warning",
            threshold=threshold,
        )
    else:
        logger.info("Normal operation", threshold=threshold)
    
    return {"threshold": threshold}


# Example 8: Database operation logging
async def create_user(user_id: int, username: str):
    """Example database operation with logging."""
    db_logger.info(
        "Creating user",
        user_id=user_id,
        username=username,
        operation="INSERT",
    )
    
    try:
        # Simulate DB operation
        # await session.execute(...)
        
        db_logger.info(
            "User created successfully",
            user_id=user_id,
            duration_ms=15.3,
        )
    
    except Exception as exc:
        db_logger.exception(
            "Failed to create user",
            user_id=user_id,
            username=username,
        )
        raise


if __name__ == "__main__":
    import uvicorn
    
    # Logs will be in JSON format
    uvicorn.run(app, host="0.0.0.0", port=8000)
