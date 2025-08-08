"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from app.main import app

client = TestClient(app)


class TestAPIEndpoints:
    """Test cases for API endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "LLM Gateway API"
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "llm-gateway"
    
    def test_v1_health_endpoint(self):
        """Test v1 health check endpoint."""
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "redis_connected" in data
        assert "version" in data
    
    def test_models_endpoint(self):
        """Test models endpoint."""
        response = client.get("/v1/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0
        
        # Check model structure
        model = data["models"][0]
        assert "model" in model
        assert "cost_per_token" in model
        assert "cost_per_1k_tokens" in model
    
    def test_cache_stats_endpoint(self):
        """Test cache stats endpoint."""
        response = client.get("/v1/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "cache_ttl_seconds" in data
        assert "timestamp" in data
    
    def test_admin_summary_endpoint(self):
        """Test admin summary endpoint."""
        response = client.get("/v1/admin/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert "cache" in data
        assert "costs" in data
        assert "rate_limits" in data
        assert "retry_config" in data
    
    @patch('app.services.llm_client.openai.ChatCompletion.acreate')
    def test_generate_endpoint_success(self, mock_openai):
        """Test successful text generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated text"
        mock_response.usage = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
        mock_openai.return_value = mock_response
        
        request_data = {
            "prompt": "Test prompt",
            "model": "gpt-4",
            "temperature": 0.7,
            "user_id": "test_user"
        }
        
        response = client.post("/v1/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "completion" in data
        assert "total_tokens" in data
        assert "cost_usd" in data
        assert data["completion"] == "Generated text"
    
    def test_generate_endpoint_invalid_model(self):
        """Test generation with invalid model."""
        request_data = {
            "prompt": "Test prompt",
            "model": "invalid-model",
            "temperature": 0.7,
            "user_id": "test_user"
        }
        
        response = client.post("/v1/generate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_generate_endpoint_missing_user_id(self):
        """Test generation without user_id."""
        request_data = {
            "prompt": "Test prompt",
            "model": "gpt-4",
            "temperature": 0.7
        }
        
        response = client.post("/v1/generate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_generate_endpoint_invalid_temperature(self):
        """Test generation with invalid temperature."""
        request_data = {
            "prompt": "Test prompt",
            "model": "gpt-4",
            "temperature": 3.0,  # Invalid temperature
            "user_id": "test_user"
        }
        
        response = client.post("/v1/generate", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_usage_endpoint(self):
        """Test usage endpoint."""
        response = client.get("/v1/usage/test_user")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "total_requests" in data
        assert "total_cost_usd" in data
    
    def test_rate_limit_info_endpoint(self):
        """Test rate limit info endpoint."""
        response = client.get("/v1/rate-limit/test_user")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "minute_requests" in data
        assert "hour_requests" in data
    
    def test_clear_cache_endpoint(self):
        """Test clear cache endpoint."""
        response = client.delete("/v1/cache/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Cleared" in data["message"]
    
    def test_request_headers(self):
        """Test that request headers are properly set."""
        response = client.get("/health")
        
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers
        assert response.headers["X-Request-ID"] is not None
        assert response.headers["X-Process-Time"] is not None 