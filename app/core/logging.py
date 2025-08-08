"""
Custom logging setup for the LLM Gateway API.

This module provides structured logging with custom formatters
and handlers for better observability in production environments.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


def setup_logging() -> None:
    """Initialize logging configuration for the application."""
    # Create logger
    logger = logging.getLogger("llm_gateway")
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatter and add to handler
    formatter = StructuredFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Set up third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def log_request(
    user_id: str,
    prompt: str,
    model: str,
    temperature: float,
    request_id: str,
    **kwargs: Any
) -> None:
    """Log incoming request details."""
    logger = logging.getLogger("llm_gateway")
    logger.info(
        "Incoming request",
        extra={
            "extra_fields": {
                "event_type": "request_received",
                "user_id": user_id,
                "model": model,
                "temperature": temperature,
                "request_id": request_id,
                "prompt_length": len(prompt),
                **kwargs
            }
        }
    )


def log_response(
    user_id: str,
    model: str,
    total_tokens: int,
    cost: float,
    latency_ms: float,
    request_id: str,
    **kwargs: Any
) -> None:
    """Log response details and cost information."""
    logger = logging.getLogger("llm_gateway")
    logger.info(
        "Response generated",
        extra={
            "extra_fields": {
                "event_type": "response_generated",
                "user_id": user_id,
                "model": model,
                "total_tokens": total_tokens,
                "cost_usd": round(cost, 6),
                "latency_ms": round(latency_ms, 2),
                "request_id": request_id,
                **kwargs
            }
        }
    )


def log_error(
    user_id: str,
    error_type: str,
    error_message: str,
    request_id: str,
    **kwargs: Any
) -> None:
    """Log error details."""
    logger = logging.getLogger("llm_gateway")
    logger.error(
        "Request failed",
        extra={
            "extra_fields": {
                "event_type": "request_failed",
                "user_id": user_id,
                "error_type": error_type,
                "error_message": error_message,
                "request_id": request_id,
                **kwargs
            }
        }
    )


def log_rate_limit_exceeded(user_id: str, window: str) -> None:
    """Log rate limit exceeded events."""
    logger = logging.getLogger("llm_gateway")
    logger.warning(
        "Rate limit exceeded",
        extra={
            "extra_fields": {
                "event_type": "rate_limit_exceeded",
                "user_id": user_id,
                "window": window,
            }
        }
    )


def log_cache_hit(user_id: str, prompt_hash: str) -> None:
    """Log cache hit events."""
    logger = logging.getLogger("llm_gateway")
    logger.info(
        "Cache hit",
        extra={
            "extra_fields": {
                "event_type": "cache_hit",
                "user_id": user_id,
                "prompt_hash": prompt_hash,
            }
        }
    ) 