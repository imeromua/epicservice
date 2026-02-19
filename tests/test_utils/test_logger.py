"""Tests for structured logger."""

import json
import logging
from io import StringIO

import pytest

from utils.logger import (
    StructuredLogger,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
)


@pytest.fixture
def logger_with_stream():
    """Create logger with StringIO stream for testing."""
    stream = StringIO()
    logger = StructuredLogger("test")
    
    # Replace handler with StringIO handler
    logger.logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    from utils.logger import StructuredFormatter
    handler.setFormatter(StructuredFormatter())
    logger.logger.addHandler(handler)
    
    return logger, stream


def test_structured_log_format(logger_with_stream):
    """Test that logs are in JSON format."""
    logger, stream = logger_with_stream
    
    logger.info("Test message")
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert "timestamp" in log_data
    assert "logger" in log_data


def test_correlation_id(logger_with_stream):
    """Test correlation ID in logs."""
    logger, stream = logger_with_stream
    
    set_correlation_id("test-123")
    logger.info("Test message")
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["correlation_id"] == "test-123"
    
    # Cleanup
    clear_correlation_id()


def test_extra_fields(logger_with_stream):
    """Test extra fields in logs."""
    logger, stream = logger_with_stream
    
    logger.info("Test", user_id=123, action="search")
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["extra"]["user_id"] == 123
    assert log_data["extra"]["action"] == "search"


def test_exception_logging(logger_with_stream):
    """Test exception logging."""
    logger, stream = logger_with_stream
    
    try:
        raise ValueError("Test error")
    except ValueError:
        logger.exception("Error occurred")
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data["level"] == "ERROR"
    assert "exception" in log_data
    assert "ValueError" in log_data["exception"]


def test_get_set_clear_correlation_id():
    """Test correlation ID context management."""
    # Initially None
    assert get_correlation_id() is None
    
    # Set
    set_correlation_id("abc-123")
    assert get_correlation_id() == "abc-123"
    
    # Clear
    clear_correlation_id()
    assert get_correlation_id() is None
