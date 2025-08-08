"""
Pydantic schemas for API request and response models.

This module defines the data models used for API requests and responses,
ensuring type safety and proper validation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class PromptRequest(BaseModel):
    """Request model for text generation."""
    
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The input prompt for text generation"
    )
    model: str = Field(
        default="gpt-4",
        description="The LLM model to use for generation"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Controls randomness in generation (0.0 = deterministic, 2.0 = very random)"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=4000,
        description="Maximum number of tokens to generate"
    )
    user_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the user"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Optional request identifier for tracking"
    )
    
    @validator('model')
    def validate_model(cls, v):
        """Validate that the model is supported."""
        supported_models = [
            "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
            "claude-3-opus", "claude-3-sonnet", "claude-3-haiku"
        ]
        if v not in supported_models:
            raise ValueError(f"Model {v} is not supported. Supported models: {supported_models}")
        return v


class PromptResponse(BaseModel):
    """Response model for text generation."""
    
    completion: str = Field(
        ...,
        description="The generated text completion"
    )
    model: str = Field(
        ...,
        description="The model used for generation"
    )
    total_tokens: int = Field(
        ...,
        ge=0,
        description="Total number of tokens used (prompt + completion)"
    )
    prompt_tokens: int = Field(
        ...,
        ge=0,
        description="Number of tokens in the prompt"
    )
    completion_tokens: int = Field(
        ...,
        ge=0,
        description="Number of tokens in the completion"
    )
    cost_usd: float = Field(
        ...,
        ge=0.0,
        description="Cost of the request in USD"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request identifier for tracking"
    )
    cached: bool = Field(
        default=False,
        description="Whether the response was served from cache"
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Request latency in milliseconds"
    )


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(
        ...,
        description="Error message"
    )
    error_type: str = Field(
        ...,
        description="Type of error"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request identifier for tracking"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the error"
    )


class RateLimitResponse(BaseModel):
    """Rate limit exceeded response model."""
    
    error: str = Field(
        default="Rate limit exceeded",
        description="Error message"
    )
    window: str = Field(
        ...,
        description="Time window for the rate limit"
    )
    retry_after: int = Field(
        ...,
        description="Seconds to wait before retrying"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request identifier for tracking"
    )


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(
        default="healthy",
        description="Service health status"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the health check"
    )
    version: str = Field(
        default="1.0.0",
        description="API version"
    )
    redis_connected: bool = Field(
        ...,
        description="Whether Redis is connected"
    )


class UsageResponse(BaseModel):
    """Usage statistics response model."""
    
    user_id: str = Field(
        ...,
        description="User identifier"
    )
    total_requests: int = Field(
        ...,
        ge=0,
        description="Total number of requests"
    )
    total_tokens: int = Field(
        ...,
        ge=0,
        description="Total number of tokens used"
    )
    total_cost_usd: float = Field(
        ...,
        ge=0.0,
        description="Total cost in USD"
    )
    average_cost_per_request: float = Field(
        ...,
        ge=0.0,
        description="Average cost per request"
    )
    model_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by model"
    )
    time_period: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Time period for the statistics"
    )


class CacheStatsResponse(BaseModel):
    """Cache statistics response model."""
    
    enabled: bool = Field(
        ...,
        description="Whether caching is enabled"
    )
    total_cached_items: Optional[int] = Field(
        default=None,
        description="Total number of cached items"
    )
    memory_usage: Optional[str] = Field(
        default=None,
        description="Memory usage of the cache"
    )
    cache_ttl_seconds: int = Field(
        ...,
        description="Cache TTL in seconds"
    )
    timestamp: float = Field(
        ...,
        description="Timestamp of the statistics"
    )


class ModelInfoResponse(BaseModel):
    """Model information response model."""
    
    model: str = Field(
        ...,
        description="Model name"
    )
    cost_per_token: float = Field(
        ...,
        description="Cost per token"
    )
    cost_per_1k_tokens: float = Field(
        ...,
        description="Cost per 1000 tokens"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens for this model"
    )
    supported_features: List[str] = Field(
        default_factory=list,
        description="Supported features for this model"
    )


class ModelsResponse(BaseModel):
    """Response model for available models."""
    
    models: List[ModelInfoResponse] = Field(
        ...,
        description="List of available models"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the response"
    ) 