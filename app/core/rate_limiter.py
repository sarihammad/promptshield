"""
Redis-based rate limiting with sliding window implementation.

This module provides rate limiting functionality using Redis to track
user requests across different time windows (per minute, per hour).
"""

import time
from typing import Optional, Tuple
import redis
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import log_rate_limit_exceeded

# Redis client instance
redis_client = redis.from_url(settings.redis_url)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, window: str, retry_after: int):
        self.window = window
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {window} window")


def get_sliding_window_key(user_id: str, window_seconds: int) -> str:
    """Generate Redis key for sliding window rate limiting."""
    current_time = int(time.time())
    window_start = current_time - (current_time % window_seconds)
    return f"rate_limit:{user_id}:{window_seconds}:{window_start}"


def enforce_rate_limit(
    user_id: str,
    max_requests: Optional[int] = None,
    window_seconds: int = 60
) -> None:
    """
    Enforce rate limiting for a user.
    
    Args:
        user_id: Unique identifier for the user
        max_requests: Maximum number of requests allowed in the window
        window_seconds: Time window in seconds
    
    Raises:
        RateLimitExceeded: When rate limit is exceeded
    """
    max_requests = max_requests or settings.max_requests_per_minute
    
    try:
        # Get the current window key
        current_key = get_sliding_window_key(user_id, window_seconds)
        
        # Use Redis pipeline for atomic operations
        pipe = redis_client.pipeline()
        
        # Increment the counter for current window
        pipe.incr(current_key)
        pipe.expire(current_key, window_seconds)
        
        # Get the previous window key
        current_time = int(time.time())
        window_start = current_time - (current_time % window_seconds)
        previous_window_start = window_start - window_seconds
        previous_key = f"rate_limit:{user_id}:{window_seconds}:{previous_window_start}"
        
        # Get count from previous window
        pipe.get(previous_key)
        
        # Execute pipeline
        results = pipe.execute()
        current_count = results[0]
        previous_count = results[2] or 0
        
        # Calculate weighted count (sliding window)
        time_in_current_window = current_time - window_start
        weight = time_in_current_window / window_seconds
        weighted_count = int(previous_count) * (1 - weight) + current_count
        
        if weighted_count > max_requests:
            # Calculate retry after time
            retry_after = window_seconds - time_in_current_window
            
            # Log the rate limit exceeded event
            window_name = f"{window_seconds}s"
            log_rate_limit_exceeded(user_id, window_name)
            
            raise RateLimitExceeded(window_name, retry_after)
            
    except redis.RedisError as e:
        # If Redis is unavailable, log warning but allow request
        import logging
        logger = logging.getLogger("llm_gateway")
        logger.warning(f"Redis unavailable for rate limiting: {e}")
        return


def enforce_minute_rate_limit(user_id: str) -> None:
    """Enforce per-minute rate limiting."""
    enforce_rate_limit(
        user_id=user_id,
        max_requests=settings.max_requests_per_minute,
        window_seconds=60
    )


def enforce_hour_rate_limit(user_id: str) -> None:
    """Enforce per-hour rate limiting."""
    enforce_rate_limit(
        user_id=user_id,
        max_requests=settings.max_requests_per_hour,
        window_seconds=3600
    )


def get_rate_limit_info(user_id: str) -> dict:
    """
    Get current rate limit information for a user.
    
    Returns:
        Dictionary with rate limit information
    """
    try:
        current_time = int(time.time())
        
        # Get minute window info
        minute_window_start = current_time - (current_time % 60)
        minute_key = f"rate_limit:{user_id}:60:{minute_window_start}"
        minute_count = redis_client.get(minute_key) or 0
        
        # Get hour window info
        hour_window_start = current_time - (current_time % 3600)
        hour_key = f"rate_limit:{user_id}:3600:{hour_window_start}"
        hour_count = redis_client.get(hour_key) or 0
        
        return {
            "user_id": user_id,
            "minute_requests": int(minute_count),
            "minute_limit": settings.max_requests_per_minute,
            "hour_requests": int(hour_count),
            "hour_limit": settings.max_requests_per_hour,
            "timestamp": current_time
        }
        
    except redis.RedisError as e:
        import logging
        logger = logging.getLogger("llm_gateway")
        logger.warning(f"Redis unavailable for rate limit info: {e}")
        return {
            "user_id": user_id,
            "error": "Rate limit info unavailable",
            "timestamp": int(time.time())
        }


def reset_rate_limit(user_id: str) -> None:
    """Reset rate limit counters for a user (admin function)."""
    try:
        # Get all keys for this user
        pattern = f"rate_limit:{user_id}:*"
        keys = redis_client.keys(pattern)
        
        if keys:
            redis_client.delete(*keys)
            
    except redis.RedisError as e:
        import logging
        logger = logging.getLogger("llm_gateway")
        logger.warning(f"Redis unavailable for rate limit reset: {e}")


def create_rate_limit_middleware():
    """Create FastAPI middleware for automatic rate limiting."""
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse
    
    class RateLimitMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Skip rate limiting for certain paths
            if request.url.path in ["/health", "/docs", "/openapi.json"]:
                return await call_next(request)
            
            # Extract user_id from headers or query params
            user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")
            
            if not user_id:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "User ID required for rate limiting"}
                )
            
            try:
                # Enforce both minute and hour rate limits
                enforce_minute_rate_limit(user_id)
                enforce_hour_rate_limit(user_id)
                
            except RateLimitExceeded as e:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "window": e.window,
                        "retry_after": e.retry_after
                    },
                    headers={"Retry-After": str(e.retry_after)}
                )
            
            return await call_next(request)
    
    return RateLimitMiddleware 