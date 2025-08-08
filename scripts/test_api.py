#!/usr/bin/env python3
"""
Simple test script for the LLM Gateway API.

This script demonstrates basic API usage and can be used for testing
the gateway functionality.
"""

import requests
import json
import time
from typing import Dict, Any


class LLMGatewayClient:
    """Simple client for testing the LLM Gateway API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = self.session.get(f"{self.base_url}/v1/health")
        return response.json()
    
    def generate_text(
        self,
        prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        user_id: str = "test_user"
    ) -> Dict[str, Any]:
        """Generate text using the API."""
        data = {
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "user_id": user_id
        }
        
        response = self.session.post(
            f"{self.base_url}/v1/generate",
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_models(self) -> Dict[str, Any]:
        """Get available models."""
        response = self.session.get(f"{self.base_url}/v1/models")
        return response.json()
    
    def get_usage(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics."""
        response = self.session.get(f"{self.base_url}/v1/usage/{user_id}")
        return response.json()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        response = self.session.get(f"{self.base_url}/v1/cache/stats")
        return response.json()
    
    def get_admin_summary(self) -> Dict[str, Any]:
        """Get admin summary."""
        response = self.session.get(f"{self.base_url}/v1/admin/summary")
        return response.json()


def main():
    """Main test function."""
    print("🚀 LLM Gateway API Test Script")
    print("=" * 50)
    
    client = LLMGatewayClient()
    
    try:
        # Test 1: Health Check
        print("\n1. Testing Health Check...")
        health = client.health_check()
        print(f"✅ Health Status: {health['status']}")
        print(f"   Redis Connected: {health['redis_connected']}")
        print(f"   Version: {health['version']}")
        
        # Test 2: Get Available Models
        print("\n2. Testing Models Endpoint...")
        models = client.get_models()
        print(f"✅ Available Models: {len(models['models'])}")
        for model in models['models'][:3]:  # Show first 3
            print(f"   - {model['model']}: ${model['cost_per_1k_tokens']:.6f}/1k tokens")
        
        # Test 3: Generate Text
        print("\n3. Testing Text Generation...")
        start_time = time.time()
        
        response = client.generate_text(
            prompt="Explain what a transformer is in machine learning in 2 sentences.",
            model="gpt-4",
            temperature=0.7,
            user_id="test_user_123"
        )
        
        latency = time.time() - start_time
        
        print(f"✅ Generation Successful!")
        print(f"   Model: {response['model']}")
        print(f"   Completion: {response['completion'][:100]}...")
        print(f"   Tokens: {response['total_tokens']}")
        print(f"   Cost: ${response['cost_usd']:.6f}")
        print(f"   Latency: {latency:.2f}s")
        print(f"   Cached: {response['cached']}")
        
        # Test 4: Cache Statistics
        print("\n4. Testing Cache Statistics...")
        cache_stats = client.get_cache_stats()
        print(f"✅ Cache Enabled: {cache_stats['enabled']}")
        if cache_stats['enabled']:
            print(f"   Cached Items: {cache_stats.get('total_cached_items', 'N/A')}")
            print(f"   TTL: {cache_stats['cache_ttl_seconds']}s")
        
        # Test 5: Usage Statistics
        print("\n5. Testing Usage Statistics...")
        usage = client.get_usage("test_user_123")
        print(f"✅ User: {usage['user_id']}")
        print(f"   Total Requests: {usage['total_requests']}")
        print(f"   Total Cost: ${usage['total_cost_usd']:.6f}")
        
        # Test 6: Admin Summary
        print("\n6. Testing Admin Summary...")
        admin = client.get_admin_summary()
        print(f"✅ Admin Summary Retrieved")
        print(f"   Cache Enabled: {admin['cache']['enabled']}")
        print(f"   Total Requests: {admin['costs']['total_requests']}")
        print(f"   Total Cost: ${admin['costs']['total_cost_usd']:.6f}")
        
        print("\n🎉 All tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the API. Make sure it's running on http://localhost:8000")
        print("   Start the API with: uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main() 