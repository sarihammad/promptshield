"""
Retry logic with exponential backoff and jitter.

This module provides a robust retry mechanism for handling transient failures
when calling external LLM APIs. It implements exponential backoff with jitter
to prevent thundering herd problems.
"""

import asyncio
import random
import time
from typing import Any, Callable, Optional, TypeVar
from functools import wraps
import logging

from app.core.config import settings

logger = logging.getLogger("llm_gateway")

T = TypeVar('T')


class RetryableError(Exception):
    """Base exception for retryable errors."""
    pass


class RateLimitError(RetryableError):
    """Exception raised when rate limit is exceeded."""
    pass


class TimeoutError(RetryableError):
    """Exception raised when request times out."""
    pass


class ServerError(RetryableError):
    """Exception raised for 5xx server errors."""
    pass


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error is retryable."""
    retryable_error_types = (
        RateLimitError,
        TimeoutError,
        ServerError,
        ConnectionError,
        OSError,
    )
    
    # Check for specific error messages that indicate retryable conditions
    error_message = str(error).lower()
    retryable_keywords = [
        "rate limit",
        "timeout",
        "server error",
        "internal server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "connection",
        "network",
    ]
    
    return (
        isinstance(error, retryable_error_types) or
        any(keyword in error_message for keyword in retryable_keywords)
    )


def calculate_backoff_delay(attempt: int, base_delay: float) -> float:
    """Calculate exponential backoff delay with jitter."""
    # Exponential backoff: base_delay * 2^attempt
    exponential_delay = base_delay * (2 ** attempt)
    
    # Add jitter: random factor between 0.5 and 1.5
    jitter_factor = 0.5 + random.random()
    
    return exponential_delay * jitter_factor


def retry_request(
    func: Callable[..., T],
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[tuple] = None,
) -> Callable[..., T]:
    """
    Decorator to retry function calls with exponential backoff.
    
    Args:
        func: The function to retry
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exception types to retry on
    
    Returns:
        Decorated function with retry logic
    """
    max_attempts = max_attempts or settings.max_retry_attempts
    base_delay = base_delay or settings.retry_base_delay
    retryable_exceptions = retryable_exceptions or (Exception,)
    
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e
                
                # Don't retry on the last attempt
                if attempt == max_attempts - 1:
                    logger.error(
                        f"Final retry attempt failed for {func.__name__}",
                        extra={
                            "extra_fields": {
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                        }
                    )
                    raise
                
                # Check if error is retryable
                if not is_retryable_error(e):
                    logger.warning(
                        f"Non-retryable error encountered: {type(e).__name__}: {e}"
                    )
                    raise
                
                # Calculate delay for next attempt
                delay = min(
                    calculate_backoff_delay(attempt, base_delay),
                    max_delay
                )
                
                logger.warning(
                    f"Retry attempt {attempt + 1}/{max_attempts} for {func.__name__}",
                    extra={
                        "extra_fields": {
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "delay_seconds": round(delay, 2),
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    }
                )
                
                time.sleep(delay)
        
        # This should never be reached, but just in case
        raise last_exception
    
    return wrapper


async def retry_request_async(
    func: Callable[..., T],
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[tuple] = None,
) -> Callable[..., T]:
    """
    Async decorator to retry function calls with exponential backoff.
    
    Args:
        func: The async function to retry
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exception types to retry on
    
    Returns:
        Decorated async function with retry logic
    """
    max_attempts = max_attempts or settings.max_retry_attempts
    base_delay = base_delay or settings.retry_base_delay
    retryable_exceptions = retryable_exceptions or (Exception,)
    
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e
                
                # Don't retry on the last attempt
                if attempt == max_attempts - 1:
                    logger.error(
                        f"Final retry attempt failed for {func.__name__}",
                        extra={
                            "extra_fields": {
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                        }
                    )
                    raise
                
                # Check if error is retryable
                if not is_retryable_error(e):
                    logger.warning(
                        f"Non-retryable error encountered: {type(e).__name__}: {e}"
                    )
                    raise
                
                # Calculate delay for next attempt
                delay = min(
                    calculate_backoff_delay(attempt, base_delay),
                    max_delay
                )
                
                logger.warning(
                    f"Retry attempt {attempt + 1}/{max_attempts} for {func.__name__}",
                    extra={
                        "extra_fields": {
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "delay_seconds": round(delay, 2),
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    }
                )
                
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        raise last_exception
    
    return wrapper 