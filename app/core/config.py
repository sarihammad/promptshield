"""
Core configuration module for the LLM Gateway API.

This module handles all environment variables and application settings
using Pydantic's BaseSettings for type safety and validation.
"""

from typing import Dict, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Provider API Keys
    openai_api_key: str = Field(..., description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    
    # Cost Configuration (per 1K tokens)
    cost_per_token_gpt4: float = Field(default=0.00003, description="Cost per token for GPT-4")
    cost_per_token_gpt35: float = Field(default=0.000002, description="Cost per token for GPT-3.5")
    cost_per_token_claude: float = Field(default=0.000015, description="Cost per token for Claude")
    
    # Rate Limiting
    max_requests_per_minute: int = Field(default=10, description="Max requests per minute per user")
    max_requests_per_hour: int = Field(default=100, description="Max requests per hour per user")
    
    # Retry Configuration
    max_retry_attempts: int = Field(default=3, description="Maximum retry attempts for failed requests")
    retry_base_delay: float = Field(default=1.0, description="Base delay for exponential backoff")
    
    # Cache Configuration
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # API Configuration
    api_title: str = Field(default="LLM Gateway API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    api_description: str = Field(
        default="Production-grade API gateway for LLM providers with retry logic and cost control",
        description="API description"
    )
    
    @property
    def cost_per_token_map(self) -> Dict[str, float]:
        """Get cost per token mapping for different models."""
        return {
            "gpt-4": self.cost_per_token_gpt4,
            "gpt-4-turbo": self.cost_per_token_gpt4,
            "gpt-3.5-turbo": self.cost_per_token_gpt35,
            "claude-3-opus": self.cost_per_token_claude,
            "claude-3-sonnet": self.cost_per_token_claude,
            "claude-3-haiku": self.cost_per_token_claude,
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 