"""Tests for product schemas."""

import pytest
from pydantic import ValidationError
from schemas.product import (
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductSearchResponse,
)


def test_product_base_valid():
    """Test ProductBase with valid data."""
    product = ProductBase(
        article="TEST001",
        name="Test Product",
        department="DSK",
        group_name="Group A",
        price=100.50,
        available=10,
    )
    
    assert product.article == "TEST001"
    assert product.price == 100.50
    assert product.available == 10


def test_product_base_invalid_price():
    """Test ProductBase with invalid price (too many decimals)."""
    with pytest.raises(ValidationError) as exc_info:
        ProductBase(
            article="TEST001",
            name="Test Product",
            department="DSK",
            price=100.505,  # 3 decimal places
            available=10,
        )
    
    assert "Price must have at most 2 decimal places" in str(exc_info.value)


def test_product_base_negative_price():
    """Test ProductBase with negative price."""
    with pytest.raises(ValidationError):
        ProductBase(
            article="TEST001",
            name="Test Product",
            department="DSK",
            price=-100.00,
            available=10,
        )


def test_product_base_negative_available():
    """Test ProductBase with negative available."""
    with pytest.raises(ValidationError):
        ProductBase(
            article="TEST001",
            name="Test Product",
            department="DSK",
            price=100.00,
            available=-5,
        )


def test_product_create_with_defaults():
    """Test ProductCreate with default values."""
    product = ProductCreate(
        article="TEST001",
        name="Test Product",
        department="DSK",
        price=100.00,
        available=10,
    )
    
    assert product.no_movement == 0
    assert product.is_active is True


def test_product_update_partial():
    """Test ProductUpdate with partial data."""
    update = ProductUpdate(price=150.00, available=20)
    
    assert update.price == 150.00
    assert update.available == 20
    assert update.article is None
    assert update.name is None


def test_product_response_actual_available():
    """Test ProductResponse calculates actual_available correctly."""
    product = ProductResponse(
        id=1,
        article="TEST001",
        name="Test Product",
        department="DSK",
        price=100.00,
        available=10,
        reserved=3,
        no_movement=0,
        is_active=True,
    )
    
    assert product.actual_available == 7  # 10 - 3


def test_product_search_response():
    """Test ProductSearchResponse."""
    response = ProductSearchResponse(
        products=[
            ProductResponse(
                id=1,
                article="TEST001",
                name="Test Product",
                department="DSK",
                price=100.00,
                available=10,
                reserved=2,
                no_movement=0,
                is_active=True,
            )
        ],
        total=1,
        query="TEST",
    )
    
    assert response.total == 1
    assert len(response.products) == 1
    assert response.query == "TEST"
