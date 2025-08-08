"""
Unit tests for rate limiter module.
"""

import pytest
import time
from unittest.mock import Mock, patch
from app.core.rate_limiter import (
    enforce_rate_limit, enforce_minute_rate_limit, enforce_hour_rate_limit,
    get_rate_limit_info, RateLimitExceeded
)


class TestRateLimiter:
    """Test cases for rate limiting functionality."""
    
    @patch('app.core.rate_limiter.redis_client')
    def test_enforce_rate_limit_success(self, mock_redis):
        """Test successful rate limit enforcement."""
        # Mock Redis responses
        mock_redis.pipeline.return_value.execute.return_value = [1, None, 0]
        
        # Should not raise exception
        enforce_rate_limit("user123", max_requests=10, window_seconds=60)
        
        # Verify Redis was called
        mock_redis.pipeline.assert_called_once()
    
    @patch('app.core.rate_limiter.redis_client')
    def test_enforce_rate_limit_exceeded(self, mock_redis):
        """Test rate limit exceeded scenario."""
        # Mock Redis responses - weighted count exceeds limit
        mock_redis.pipeline.return_value.execute.return_value = [11, None, 5]
        
        with pytest.raises(RateLimitExceeded) as exc_info:
            enforce_rate_limit("user123", max_requests=10, window_seconds=60)
        
        assert "60s" in str(exc_info.value)
        assert exc_info.value.retry_after > 0
    
    @patch('app.core.rate_limiter.redis_client')
    def test_enforce_minute_rate_limit(self, mock_redis):
        """Test minute rate limit enforcement."""
        mock_redis.pipeline.return_value.execute.return_value = [1, None, 0]
        
        # Should not raise exception
        enforce_minute_rate_limit("user123")
        
        mock_redis.pipeline.assert_called_once()
    
    @patch('app.core.rate_limiter.redis_client')
    def test_enforce_hour_rate_limit(self, mock_redis):
        """Test hour rate limit enforcement."""
        mock_redis.pipeline.return_value.execute.return_value = [1, None, 0]
        
        # Should not raise exception
        enforce_hour_rate_limit("user123")
        
        mock_redis.pipeline.assert_called_once()
    
    @patch('app.core.rate_limiter.redis_client')
    def test_get_rate_limit_info(self, mock_redis):
        """Test rate limit info retrieval."""
        # Mock Redis responses
        mock_redis.get.side_effect = [b"5", b"25"]
        
        info = get_rate_limit_info("user123")
        
        assert info["user_id"] == "user123"
        assert info["minute_requests"] == 5
        assert info["hour_requests"] == 25
        assert "timestamp" in info
    
    @patch('app.core.rate_limiter.redis_client')
    def test_get_rate_limit_info_redis_error(self, mock_redis):
        """Test rate limit info with Redis error."""
        mock_redis.get.side_effect = Exception("Redis error")
        
        info = get_rate_limit_info("user123")
        
        assert info["user_id"] == "user123"
        assert "error" in info
        assert info["error"] == "Rate limit info unavailable"
    
    @patch('app.core.rate_limiter.redis_client')
    def test_enforce_rate_limit_redis_error(self, mock_redis):
        """Test rate limit enforcement with Redis error."""
        mock_redis.pipeline.side_effect = Exception("Redis error")
        
        # Should not raise exception when Redis is unavailable
        enforce_rate_limit("user123", max_requests=10, window_seconds=60)
    
    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceeded exception properties."""
        exception = RateLimitExceeded("60s", 30)
        
        assert exception.window == "60s"
        assert exception.retry_after == 30
        assert "Rate limit exceeded for 60s window" in str(exception) 