"""
Unit tests for retry logic module.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.core.retry import (
    retry_request, retry_request_async, is_retryable_error,
    calculate_backoff_delay, RetryableError, RateLimitError
)


class TestRetryLogic:
    """Test cases for retry logic functionality."""
    
    def test_calculate_backoff_delay(self):
        """Test exponential backoff delay calculation."""
        # Test base delay
        delay = calculate_backoff_delay(0, 1.0)
        assert 0.5 <= delay <= 1.5  # With jitter
        
        # Test exponential increase
        delay1 = calculate_backoff_delay(1, 1.0)
        delay2 = calculate_backoff_delay(2, 1.0)
        assert delay2 > delay1
        
        # Test max delay
        delay = calculate_backoff_delay(10, 1.0)
        assert delay <= 60.0  # Max delay
    
    def test_is_retryable_error(self):
        """Test retryable error detection."""
        # Test retryable errors
        assert is_retryable_error(RateLimitError("rate limit"))
        assert is_retryable_error(ConnectionError("connection failed"))
        
        # Test non-retryable errors
        assert not is_retryable_error(ValueError("invalid input"))
        assert not is_retryable_error(TypeError("type error"))
        
        # Test error message matching
        error = Exception("rate limit exceeded")
        assert is_retryable_error(error)
        
        error = Exception("timeout occurred")
        assert is_retryable_error(error)
    
    def test_retry_request_success(self):
        """Test successful retry without failures."""
        mock_func = Mock(return_value="success")
        
        decorated_func = retry_request()(mock_func)
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_request_failure_then_success(self):
        """Test retry with initial failure then success."""
        mock_func = Mock(side_effect=[RateLimitError("rate limit"), "success"])
        
        decorated_func = retry_request(max_attempts=2)(mock_func)
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_retry_request_all_failures(self):
        """Test retry with all attempts failing."""
        mock_func = Mock(side_effect=RateLimitError("rate limit"))
        
        decorated_func = retry_request(max_attempts=3)(mock_func)
        
        with pytest.raises(RateLimitError):
            decorated_func()
        
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_request_async_success(self):
        """Test successful async retry without failures."""
        async def mock_async_func():
            return "success"
        
        decorated_func = retry_request_async()(mock_async_func)
        result = await decorated_func()
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_request_async_failure_then_success(self):
        """Test async retry with initial failure then success."""
        call_count = 0
        
        async def mock_async_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("rate limit")
            return "success"
        
        decorated_func = retry_request_async(max_attempts=2)(mock_async_func)
        result = await decorated_func()
        
        assert result == "success"
        assert call_count == 2
    
    def test_retry_request_non_retryable_error(self):
        """Test that non-retryable errors are not retried."""
        mock_func = Mock(side_effect=ValueError("invalid input"))
        
        decorated_func = retry_request()(mock_func)
        
        with pytest.raises(ValueError):
            decorated_func()
        
        assert mock_func.call_count == 1  # Should not retry 