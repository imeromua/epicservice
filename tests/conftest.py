"""Pytest configuration and fixtures"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from database.models import Base
from config import settings

# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def test_user_id() -> int:
    """Test user Telegram ID"""
    return 123456789


@pytest.fixture
def test_admin_id() -> int:
    """Test admin Telegram ID"""
    return 111111111


@pytest.fixture
async def sample_product(test_session: AsyncSession) -> dict:
    """Create sample product for testing"""
    from database.models import Product
    
    product = Product(
        article="TEST001",
        name="Test Product",
        department="Test Department",
        group_name="Test Group",
        price=100.0,
        available=10,
        reserved=0,
        no_movement=0,
        is_active=True
    )
    
    test_session.add(product)
    await test_session.commit()
    await test_session.refresh(product)
    
    return {
        "id": product.id,
        "article": product.article,
        "name": product.name,
        "department": product.department,
        "price": product.price,
        "available": product.available
    }
