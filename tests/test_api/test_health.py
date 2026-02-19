"""Test health check endpoint"""
import pytest
from httpx import AsyncClient
from webapp.api import app


@pytest.mark.asyncio
async def test_health_check():
    """Test /health endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ok"
    assert data["service"] == "epicservice"
    assert "version" in data
