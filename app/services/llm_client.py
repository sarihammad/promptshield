"""
LLM client service for communicating with OpenAI and Anthropic APIs.

This module provides a unified interface for calling different LLM providers
with proper error handling, retry logic, and response formatting.
"""

import time
import uuid
from typing import Dict, Any, Optional
import logging

import openai
from anthropic import Anthropic

from app.core.config import settings
from app.core.retry import retry_request_async, RetryableError
from app.core.cost_tracker import parse_token_usage, TokenUsage
from app.api.v1.schemas import PromptRequest, PromptResponse

logger = logging.getLogger("llm_gateway")

# Initialize clients
openai.api_key = settings.openai_api_key
anthropic_client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class OpenAIClient:
    """Client for OpenAI API calls."""
    
    @staticmethod
    async def generate_text(request: PromptRequest) -> PromptResponse:
        """
        Generate text using OpenAI API.
        
        Args:
            request: The generation request
            
        Returns:
            PromptResponse with generated text and metadata
        """
        start_time = time.time()
        
        @retry_request_async()
        async def _call_openai():
            """Make the actual OpenAI API call with retry logic."""
            try:
                response = await openai.ChatCompletion.acreate(
                    model=request.model,
                    messages=[{"role": "user", "content": request.prompt}],
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
                
                # Parse token usage
                token_usage = parse_token_usage(response, request.model)
                
                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000
                
                return PromptResponse(
                    completion=response.choices[0].message.content,
                    model=request.model,
                    total_tokens=token_usage.total_tokens,
                    prompt_tokens=token_usage.prompt_tokens,
                    completion_tokens=token_usage.completion_tokens,
                    cost_usd=token_usage.cost_usd,
                    request_id=request.request_id,
                    latency_ms=latency_ms
                )
                
            except openai.error.RateLimitError as e:
                logger.warning(f"OpenAI rate limit error: {e}")
                raise RetryableError(f"Rate limit error: {e}")
                
            except openai.error.Timeout as e:
                logger.warning(f"OpenAI timeout error: {e}")
                raise RetryableError(f"Timeout error: {e}")
                
            except openai.error.APIError as e:
                logger.error(f"OpenAI API error: {e}")
                raise RetryableError(f"API error: {e}")
                
            except Exception as e:
                logger.error(f"Unexpected OpenAI error: {e}")
                raise LLMProviderError(f"OpenAI error: {e}")
        
        return await _call_openai()


class AnthropicClient:
    """Client for Anthropic API calls."""
    
    @staticmethod
    async def generate_text(request: PromptRequest) -> PromptResponse:
        """
        Generate text using Anthropic API.
        
        Args:
            request: The generation request
            
        Returns:
            PromptResponse with generated text and metadata
        """
        if not anthropic_client:
            raise LLMProviderError("Anthropic client not configured")
        
        start_time = time.time()
        
        @retry_request_async()
        async def _call_anthropic():
            """Make the actual Anthropic API call with retry logic."""
            try:
                response = await anthropic_client.messages.create(
                    model=request.model,
                    max_tokens=request.max_tokens or 1000,
                    temperature=request.temperature,
                    messages=[{"role": "user", "content": request.prompt}]
                )
                
                # Anthropic response structure is different
                # We need to estimate token usage since it's not provided
                estimated_tokens = len(request.prompt) // 4 + len(response.content[0].text) // 4
                token_usage = TokenUsage(
                    prompt_tokens=len(request.prompt) // 4,
                    completion_tokens=len(response.content[0].text) // 4,
                    total_tokens=estimated_tokens,
                    model=request.model,
                    cost_usd=estimated_tokens * settings.cost_per_token_map.get(request.model, 0.000015)
                )
                
                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000
                
                return PromptResponse(
                    completion=response.content[0].text,
                    model=request.model,
                    total_tokens=token_usage.total_tokens,
                    prompt_tokens=token_usage.prompt_tokens,
                    completion_tokens=token_usage.completion_tokens,
                    cost_usd=token_usage.cost_usd,
                    request_id=request.request_id,
                    latency_ms=latency_ms
                )
                
            except Exception as e:
                logger.error(f"Anthropic API error: {e}")
                raise RetryableError(f"Anthropic error: {e}")
        
        return await _call_anthropic()


class LLMClient:
    """Unified LLM client that routes to appropriate provider."""
    
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.anthropic_client = AnthropicClient()
    
    def _get_provider_for_model(self, model: str) -> str:
        """Determine the provider for a given model."""
        if model.startswith("gpt-"):
            return "openai"
        elif model.startswith("claude-"):
            return "anthropic"
        else:
            raise ValueError(f"Unknown model: {model}")
    
    async def generate_text(self, request: PromptRequest) -> PromptResponse:
        """
        Generate text using the appropriate LLM provider.
        
        Args:
            request: The generation request
            
        Returns:
            PromptResponse with generated text and metadata
        """
        provider = self._get_provider_for_model(request.model)
        
        if provider == "openai":
            return await self.openai_client.generate_text(request)
        elif provider == "anthropic":
            return await self.anthropic_client.generate_text(request)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def get_supported_models(self) -> Dict[str, list]:
        """Get list of supported models by provider."""
        return {
            "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
        }


# Global LLM client instance
llm_client = LLMClient()


async def call_llm(request: PromptRequest) -> PromptResponse:
    """
    Convenience function to call LLM with the global client.
    
    Args:
        request: The generation request
        
    Returns:
        PromptResponse with generated text and metadata
    """
    return await llm_client.generate_text(request) 