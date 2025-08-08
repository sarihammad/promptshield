"""
API endpoints for the LLM Gateway.

This module contains all the FastAPI route handlers for the LLM Gateway API,
including the main generation endpoint, health checks, and admin endpoints.
"""

import time
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from app.api.v1.schemas import (
    PromptRequest, PromptResponse, ErrorResponse, HealthResponse,
    UsageResponse, CacheStatsResponse, ModelsResponse, ModelInfoResponse
)
from app.services.llm_client import call_llm
from app.core.rate_limiter import enforce_minute_rate_limit, enforce_hour_rate_limit, get_rate_limit_info
from app.core.cost_tracker import cost_tracker, get_model_cost_info
from app.core.cache import cache_manager
from app.core.logging import log_request, log_response, log_error
from app.core.config import settings

router = APIRouter()


@router.post("/generate", response_model=PromptResponse)
async def generate_text(request: PromptRequest):
    """
    Generate text using the specified LLM model.
    
    This endpoint handles text generation requests with rate limiting,
    caching, cost tracking, and retry logic.
    """
    start_time = time.time()
    request_id = request.request_id or str(uuid.uuid4())
    
    try:
        # Log incoming request
        log_request(
            user_id=request.user_id,
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            request_id=request_id
        )
        
        # Check cache first
        cached_response = cache_manager.get(
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if cached_response:
            # Return cached response
            response_data = cached_response["response"]
            response = PromptResponse(
                completion=response_data["completion"],
                model=response_data["model"],
                total_tokens=response_data["total_tokens"],
                prompt_tokens=response_data["prompt_tokens"],
                completion_tokens=response_data["completion_tokens"],
                cost_usd=response_data["cost_usd"],
                request_id=request_id,
                cached=True,
                latency_ms=(time.time() - start_time) * 1000
            )
            
            # Log response
            log_response(
                user_id=request.user_id,
                model=request.model,
                total_tokens=response.total_tokens,
                cost=response.cost_usd,
                latency_ms=response.latency_ms,
                request_id=request_id
            )
            
            return response
        
        # Enforce rate limits
        enforce_minute_rate_limit(request.user_id)
        enforce_hour_rate_limit(request.user_id)
        
        # Call LLM
        response = await call_llm(request)
        
        # Update response with request_id and latency
        response.request_id = request_id
        response.latency_ms = (time.time() - start_time) * 1000
        
        # Cache the response
        cache_manager.set(
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            response={
                "completion": response.completion,
                "model": response.model,
                "total_tokens": response.total_tokens,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "cost_usd": response.cost_usd
            },
            max_tokens=request.max_tokens
        )
        
        # Track cost
        from app.core.cost_tracker import TokenUsage
        token_usage = TokenUsage(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            model=response.model,
            cost_usd=response.cost_usd
        )
        cost_tracker.track_request(
            user_id=request.user_id,
            model=response.model,
            token_usage=token_usage,
            request_id=request_id
        )
        
        # Log response
        log_response(
            user_id=request.user_id,
            model=response.model,
            total_tokens=response.total_tokens,
            cost=response.cost_usd,
            latency_ms=response.latency_ms,
            request_id=request_id
        )
        
        return response
        
    except Exception as e:
        # Log error
        log_error(
            user_id=request.user_id,
            error_type=type(e).__name__,
            error_message=str(e),
            request_id=request_id
        )
        
        # Re-raise as HTTP exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check Redis connection
        import redis
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        redis_connected = True
    except Exception:
        redis_connected = False
    
    return HealthResponse(
        status="healthy",
        version=settings.api_version,
        redis_connected=redis_connected
    )


@router.get("/usage/{user_id}", response_model=UsageResponse)
async def get_usage(user_id: str):
    """Get usage statistics for a user."""
    try:
        # Get cost summary
        summary = cost_tracker.get_summary()
        
        return UsageResponse(
            user_id=user_id,
            total_requests=summary["total_requests"],
            total_tokens=0,  # Would come from database in production
            total_cost_usd=summary["total_cost_usd"],
            average_cost_per_request=summary["average_cost_per_request"],
            model_breakdown=summary["model_breakdown"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage: {str(e)}"
        )


@router.get("/rate-limit/{user_id}")
async def get_rate_limit_info(user_id: str):
    """Get rate limit information for a user."""
    try:
        info = get_rate_limit_info(user_id)
        return info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rate limit info: {str(e)}"
        )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """Get cache statistics."""
    try:
        stats = cache_manager.stats()
        return CacheStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_cache():
    """Clear all cached responses."""
    try:
        deleted_count = cache_manager.clear()
        return {"message": f"Cleared {deleted_count} cached items"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """Get list of supported models and their cost information."""
    try:
        cost_info = get_model_cost_info()
        models = []
        
        for model, info in cost_info.items():
            model_info = ModelInfoResponse(
                model=model,
                cost_per_token=info["cost_per_token"],
                cost_per_1k_tokens=info["cost_per_1k_tokens"],
                max_tokens=4000,  # Default max tokens
                supported_features=["text-generation"]
            )
            models.append(model_info)
        
        return ModelsResponse(models=models)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get models: {str(e)}"
        )


@router.get("/admin/summary")
async def get_admin_summary():
    """Get admin summary with system statistics."""
    try:
        # Get various statistics
        cache_stats = cache_manager.stats()
        cost_summary = cost_tracker.get_summary()
        
        return {
            "cache": cache_stats,
            "costs": cost_summary,
            "rate_limits": {
                "max_requests_per_minute": settings.max_requests_per_minute,
                "max_requests_per_hour": settings.max_requests_per_hour
            },
            "retry_config": {
                "max_attempts": settings.max_retry_attempts,
                "base_delay": settings.retry_base_delay
            },
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get admin summary: {str(e)}"
        ) 