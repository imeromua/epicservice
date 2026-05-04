import pytest
import os
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import text
from unittest.mock import patch

from webapp.api import app
from database.session import async_session
from database.models import Product

client = TestClient(app)

@pytest.fixture(autouse=True)
async def setup_test_db():
    # Setup test data
    async with async_session() as session:
        # Clear existing
        await session.execute(text("DELETE FROM products"))
        
        # Add test products
        session.add_all([
            Product(
                id=1,
                артикул="RM001",
                назва="Test Product A",
                кількість="10",
                ціна=100.0,
                відділ="Test Dept 1",
                група="Group 1",
                місяці_без_руху=5
            ),
            Product(
                id=2,
                артикул="RM002",
                назва="Test Product B",
                кількість="5",
                ціна=200.0,
                відділ="Test Dept 1",
                група="Group 2",
                місяці_без_руху=8
            ),
            Product(
                id=3,
                артикул="RM003",
                назва="Test Product C",
                кількість="20",
                ціна=50.0,
                відділ="Test Dept 2",
                група="Group 1",
                місяці_без_руху=1
            )
        ])
        await session.commit()
        
    yield
    
    # Teardown
    async with async_session() as session:
        await session.execute(text("DELETE FROM products"))
        await session.commit()

@pytest.mark.asyncio
async def test_report_master_options():
    # Assuming test admin ID is in CONFIG_ADMIN_IDS
    from config import ADMIN_IDS
    admin_id = ADMIN_IDS[0] if ADMIN_IDS else 1962821395
    
    response = client.get(f"/api/admin/report-master/options?user_id={admin_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "options" in data
    assert "Test Dept 1" in data["options"]
    assert "Test Dept 2" in data["options"]
    
    # Verify groups are correct for departments
    assert "Group 1" in data["options"]["Test Dept 1"]
    assert "Group 2" in data["options"]["Test Dept 1"]
    assert "Group 1" in data["options"]["Test Dept 2"]

@pytest.mark.asyncio
async def test_report_master_generate():
    from config import ADMIN_IDS
    admin_id = ADMIN_IDS[0] if ADMIN_IDS else 1962821395
    
    # Test generation for specific department and group
    response = client.get(
        f"/api/admin/report-master/generate?user_id={admin_id}&department=Test Dept 1&group=Group 1&sort_by=name"
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    # Test file reading (we can write response content to a temp file and read with pandas)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(response.content)
        temp_path = f.name
        
    try:
        df = pd.read_excel(temp_path)
        assert len(df) == 1
        assert df.iloc[0]["Артикул"] == "RM001"
        assert df.iloc[0]["Назва"] == "Test Product A"
    finally:
        os.remove(temp_path)

@pytest.mark.asyncio
async def test_report_master_generate_all():
    from config import ADMIN_IDS
    admin_id = ADMIN_IDS[0] if ADMIN_IDS else 1962821395
    
    # Test generation with no filters
    response = client.get(
        f"/api/admin/report-master/generate?user_id={admin_id}&sort_by=sum"
    )
    
    assert response.status_code == 200
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(response.content)
        temp_path = f.name
        
    try:
        df = pd.read_excel(temp_path)
        assert len(df) == 3
        # Should be sorted by sum descending
        # RM001: 10 * 100 = 1000
        # RM002: 5 * 200 = 1000
        # RM003: 20 * 50 = 1000
        # Since they are equal, the order might vary or be stable. 
        # Just verifying all are present.
        articles = df["Артикул"].tolist()
        assert "RM001" in articles
        assert "RM002" in articles
        assert "RM003" in articles
    finally:
        os.remove(temp_path)
