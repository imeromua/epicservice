"""Test SQLAlchemy models"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Product, TempList


@pytest.mark.asyncio
async def test_user_creation(test_session: AsyncSession):
    """Test User model creation"""
    user = User(
        id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User"
    )
    
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    
    assert user.id == 123456789
    assert user.username == "testuser"
    assert user.first_name == "Test"
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_product_creation(test_session: AsyncSession):
    """Test Product model creation"""
    product = Product(
        article="TEST001",
        name="Test Product",
        department="Test Dept",
        group_name="Test Group",
        price=100.50,
        available=10,
        reserved=0,
        no_movement=0,
        is_active=True
    )
    
    test_session.add(product)
    await test_session.commit()
    await test_session.refresh(product)
    
    assert product.article == "TEST001"
    assert product.price == 100.50
    assert product.available == 10
    assert product.reserved == 0
    assert product.is_active is True


@pytest.mark.asyncio
async def test_product_reservation(test_session: AsyncSession):
    """Test product reservation logic"""
    product = Product(
        article="TEST002",
        name="Test Product 2",
        department="Test Dept",
        group_name="Test Group",
        price=50.0,
        available=10,
        reserved=0,
        no_movement=0,
        is_active=True
    )
    
    test_session.add(product)
    await test_session.commit()
    
    # Reserve 3 items
    product.reserved += 3
    await test_session.commit()
    await test_session.refresh(product)
    
    assert product.reserved == 3
    assert product.available == 10  # Available doesn't change


@pytest.mark.asyncio
async def test_temp_list_creation(test_session: AsyncSession, test_user_id: int):
    """Test TempList model creation"""
    # Create user and product first
    user = User(id=test_user_id, username="testuser")
    product = Product(
        article="TEST003",
        name="Test Product 3",
        department="Test Dept",
        group_name="Test Group",
        price=25.0,
        available=5,
        reserved=0,
        no_movement=0,
        is_active=True
    )
    
    test_session.add(user)
    test_session.add(product)
    await test_session.commit()
    await test_session.refresh(product)
    
    # Add to temp list
    temp_item = TempList(
        user_id=test_user_id,
        product_id=product.id,
        quantity=2
    )
    
    test_session.add(temp_item)
    await test_session.commit()
    await test_session.refresh(temp_item)
    
    assert temp_item.user_id == test_user_id
    assert temp_item.product_id == product.id
    assert temp_item.quantity == 2
