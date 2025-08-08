"""
Redis-based caching system for LLM responses.

This module provides caching functionality to store and retrieve
LLM responses, reducing API calls and improving response times.
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional
import redis

from app.core.config import settings
from app.core.logging import log_cache_hit

# Redis client instance
redis_client = redis.from_url(settings.redis_url)


def generate_cache_key(prompt: str, model: str, temperature: float, **kwargs: Any) -> str:
    """
    Generate a unique cache key based on request parameters.
    
    Args:
        prompt: The input prompt
        model: The LLM model being used
        temperature: The temperature parameter
        **kwargs: Additional parameters to include in the key
    
    Returns:
        SHA256 hash of the request parameters
    """
    # Create a dictionary of all parameters
    cache_data = {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        **kwargs
    }
    
    # Convert to JSON and hash
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_string.encode()).hexdigest()


def get_cached_response(
    prompt: str,
    model: str,
    temperature: float,
    **kwargs: Any
) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached response for a given request.
    
    Args:
        prompt: The input prompt
        model: The LLM model being used
        temperature: The temperature parameter
        **kwargs: Additional parameters
    
    Returns:
        Cached response dictionary or None if not found
    """
    try:
        cache_key = generate_cache_key(prompt, model, temperature, **kwargs)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            response_data = json.loads(cached_data)
            
            # Log cache hit
            log_cache_hit("system", cache_key)
            
            return response_data
            
    except (redis.RedisError, json.JSONDecodeError) as e:
        import logging
        logger = logging.getLogger("llm_gateway")
        logger.warning(f"Cache retrieval error: {e}")
    
    return None


def cache_response(
    prompt: str,
    model: str,
    temperature: float,
    response: Dict[str, Any],
    ttl: Optional[int] = None,
    **kwargs: Any
) -> None:
    """
    Cache a response for future requests.
    
    Args:
        prompt: The input prompt
        model: The LLM model being used
        temperature: The temperature parameter
        response: The response to cache
        ttl: Time to live in seconds (defaults to settings)
        **kwargs: Additional parameters
    """
    try:
        cache_key = generate_cache_key(prompt, model, temperature, **kwargs)
        ttl = ttl or settings.cache_ttl_seconds
        
        # Add metadata to cached response
        cached_data = {
            "response": response,
            "cached_at": time.time(),
            "cache_key": cache_key,
            "ttl": ttl
        }
        
        redis_client.setex(
            cache_key,
            ttl,
            json.dumps(cached_data)
        )
        
    except (redis.RedisError, json.JSONEncodeError) as e:
        import logging
        logger = logging.getLogger("llm_gateway")
        logger.warning(f"Cache storage error: {e}")


def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Redis pattern to match keys (e.g., "cache:*")
    
    Returns:
        Number of keys deleted
    """
    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
        return 0
        
    except redis.RedisError as e:
        import logging
        logger = logging.getLogger("llm_gateway")
        logger.warning(f"Cache invalidation error: {e}")
        return 0


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        # Get all cache keys
        cache_keys = redis_client.keys("cache:*")
        
        # Get memory usage
        info = redis_client.info("memory")
        memory_usage = info.get("used_memory_human", "N/A")
        
        return {
            "total_cached_items": len(cache_keys),
            "memory_usage": memory_usage,
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "timestamp": time.time()
        }
        
    except redis.RedisError as e:
        import logging
        logger = logging.getLogger("llm_gateway")
        logger.warning(f"Cache stats error: {e}")
        return {
            "error": "Cache statistics unavailable",
            "timestamp": time.time()
        }


def clear_cache() -> int:
    """
    Clear all cached responses.
    
    Returns:
        Number of keys deleted
    """
    return invalidate_cache("cache:*")


def is_cache_enabled() -> bool:
    """Check if caching is enabled and Redis is available."""
    try:
        redis_client.ping()
        return True
    except redis.RedisError:
        return False


class CacheManager:
    """High-level cache manager for LLM responses."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and is_cache_enabled()
    
    def get(self, prompt: str, model: str, temperature: float, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        if not self.enabled:
            return None
        
        return get_cached_response(prompt, model, temperature, **kwargs)
    
    def set(self, prompt: str, model: str, temperature: float, response: Dict[str, Any], **kwargs: Any) -> None:
        """Cache a response."""
        if not self.enabled:
            return
        
        cache_response(prompt, model, temperature, response, **kwargs)
    
    def clear(self) -> int:
        """Clear all cached responses."""
        if not self.enabled:
            return 0
        
        return clear_cache()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}
        
        stats = get_cache_stats()
        stats["enabled"] = True
        return stats


# Global cache manager instance
cache_manager = CacheManager() 