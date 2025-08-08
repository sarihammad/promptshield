"""
Cost tracking system for LLM API usage.

This module provides functionality to track token usage and calculate
costs for different LLM models, enabling cost monitoring and budgeting.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger("llm_gateway")


@dataclass
class TokenUsage:
    """Data class for token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    cost_usd: float


@dataclass
class CostRecord:
    """Data class for cost tracking records."""
    user_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: float
    request_id: Optional[str] = None


def calculate_cost(
    total_tokens: int,
    model: str,
    cost_per_token: Optional[float] = None
) -> float:
    """
    Calculate cost for token usage.
    
    Args:
        total_tokens: Total number of tokens used
        model: The LLM model used
        cost_per_token: Override cost per token (optional)
    
    Returns:
        Cost in USD
    """
    if cost_per_token is None:
        cost_per_token = settings.cost_per_token_map.get(model, 0.00003)
    
    return total_tokens * cost_per_token


def parse_token_usage(response_data: Dict[str, Any], model: str) -> TokenUsage:
    """
    Parse token usage from LLM response.
    
    Args:
        response_data: Response data from LLM API
        model: The model used
    
    Returns:
        TokenUsage object with parsed information
    """
    # Extract token usage from response
    usage = response_data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)
    
    # Calculate cost
    cost_usd = calculate_cost(total_tokens, model)
    
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
        cost_usd=cost_usd
    )


def track_cost(
    user_id: str,
    model: str,
    token_usage: TokenUsage,
    request_id: Optional[str] = None
) -> CostRecord:
    """
    Track cost for a request and log it.
    
    Args:
        user_id: User identifier
        model: The LLM model used
        token_usage: Token usage information
        request_id: Optional request identifier
    
    Returns:
        CostRecord with tracking information
    """
    cost_record = CostRecord(
        user_id=user_id,
        model=model,
        prompt_tokens=token_usage.prompt_tokens,
        completion_tokens=token_usage.completion_tokens,
        total_tokens=token_usage.total_tokens,
        cost_usd=token_usage.cost_usd,
        timestamp=time.time(),
        request_id=request_id
    )
    
    # Log the cost information
    logger.info(
        "Cost tracked",
        extra={
            "extra_fields": {
                "event_type": "cost_tracked",
                "user_id": user_id,
                "model": model,
                "prompt_tokens": token_usage.prompt_tokens,
                "completion_tokens": token_usage.completion_tokens,
                "total_tokens": token_usage.total_tokens,
                "cost_usd": round(token_usage.cost_usd, 6),
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
    
    return cost_record


def get_cost_summary(
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Get cost summary for specified filters.
    
    Args:
        user_id: Filter by user ID
        model: Filter by model
        start_time: Start timestamp
        end_time: End timestamp
    
    Returns:
        Dictionary with cost summary
    """
    # This would typically query a database
    # For now, return a placeholder structure
    return {
        "total_requests": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "average_cost_per_request": 0.0,
        "model_breakdown": {},
        "time_period": {
            "start": start_time,
            "end": end_time
        },
        "filters": {
            "user_id": user_id,
            "model": model
        }
    }


def get_model_cost_info() -> Dict[str, Dict[str, float]]:
    """
    Get cost information for all supported models.
    
    Returns:
        Dictionary mapping model names to cost information
    """
    return {
        model: {
            "cost_per_token": cost,
            "cost_per_1k_tokens": cost * 1000
        }
        for model, cost in settings.cost_per_token_map.items()
    }


def estimate_cost(
    prompt_length: int,
    estimated_completion_length: int,
    model: str
) -> float:
    """
    Estimate cost for a request before making it.
    
    Args:
        prompt_length: Estimated prompt length in characters
        estimated_completion_length: Estimated completion length in characters
        model: The model to use
    
    Returns:
        Estimated cost in USD
    """
    # Rough estimation: 1 token ≈ 4 characters
    estimated_prompt_tokens = prompt_length // 4
    estimated_completion_tokens = estimated_completion_length // 4
    total_estimated_tokens = estimated_prompt_tokens + estimated_completion_tokens
    
    return calculate_cost(total_estimated_tokens, model)


def log_cost_alert(
    user_id: str,
    cost: float,
    threshold: float = 1.0
) -> None:
    """
    Log cost alerts when spending exceeds threshold.
    
    Args:
        user_id: User identifier
        cost: Current cost
        threshold: Cost threshold for alerts
    """
    if cost > threshold:
        logger.warning(
            "Cost threshold exceeded",
            extra={
                "extra_fields": {
                    "event_type": "cost_alert",
                    "user_id": user_id,
                    "cost_usd": round(cost, 6),
                    "threshold_usd": threshold,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


class CostTracker:
    """High-level cost tracking manager."""
    
    def __init__(self):
        self.total_cost = 0.0
        self.total_requests = 0
        self.model_costs = {}
    
    def track_request(
        self,
        user_id: str,
        model: str,
        token_usage: TokenUsage,
        request_id: Optional[str] = None
    ) -> CostRecord:
        """Track cost for a single request."""
        cost_record = track_cost(user_id, model, token_usage, request_id)
        
        # Update internal tracking
        self.total_cost += cost_record.cost_usd
        self.total_requests += 1
        
        if model not in self.model_costs:
            self.model_costs[model] = 0.0
        self.model_costs[model] += cost_record.cost_usd
        
        return cost_record
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current cost summary."""
        return {
            "total_cost_usd": round(self.total_cost, 6),
            "total_requests": self.total_requests,
            "average_cost_per_request": round(
                self.total_cost / max(self.total_requests, 1), 6
            ),
            "model_breakdown": {
                model: round(cost, 6)
                for model, cost in self.model_costs.items()
            }
        }


# Global cost tracker instance
cost_tracker = CostTracker() 