#!/usr/bin/env python3
"""
API Key Utilities - Công cụ kiểm tra và xác thực OpenRouter API keys
Gộp chức năng từ check_api_key.py và verify_key.py
"""
import requests
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import pytz
from bson import ObjectId

from app.core.db_sync import api_keys_col, users_col


def mask_key(api_key: str) -> str:
    """Ẩn API key, chỉ hiện 4 ký tự cuối"""
    if not api_key or len(api_key) < 4:
        return "****"
    return ("*" * (len(api_key) - 4)) + api_key[-4:]


def verify_key_format(api_key: str) -> bool:
    """Kiểm tra format của OpenRouter API key"""
    if not api_key:
        return False
    return api_key.startswith("sk-or-") and len(api_key) > 20


def test_models_endpoint(api_key: str) -> Tuple[bool, str]:
    """Test API key bằng cách gọi models endpoint"""
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        response.raise_for_status()
        return True, "Models endpoint test passed"
    except requests.exceptions.RequestException as e:
        return False, f"Models endpoint test failed: {str(e)}"


def test_completion_endpoint(api_key: str) -> Tuple[bool, str, Optional[Dict]]:
    """Test API key bằng cách gọi completion endpoint"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://localhost",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Say 'test' in 5 words or less"}]
            },
            timeout=15
        )
        response.raise_for_status()
        return True, "Completion endpoint test passed", response.json()
    except requests.exceptions.RequestException as e:
        return False, f"Completion endpoint test failed: {str(e)}", None


def verify_openrouter_key(api_key: str, verbose: bool = True) -> Tuple[bool, List[str]]:
    """Verify OpenRouter API key bằng cách test các endpoints"""
    results = []
    
    if verbose:
        print("=" * 60)
        print("OPENROUTER API KEY VERIFICATION")
        print("=" * 60)
        print(f"\nTesting key: {mask_key(api_key)}")
        print(f"Key length: {len(api_key)} characters")

    # Check format
    if not verify_key_format(api_key):
        msg = "❌ Invalid key format! OpenRouter keys should start with 'sk-or-'"
        if verbose:
            print(msg)
        results.append(msg)
        return False, results
    
    if verbose:
        print("✅ Key format is correct")
    results.append("✅ Key format is correct")

    # Test models endpoint
    if verbose:
        print("\n--- Test 1: List Models ---")
    success, message = test_models_endpoint(api_key)
    if verbose:
        print(f"{'✅' if success else '❌'} {message}")
    results.append(f"{'✅' if success else '❌'} Models endpoint: {message}")
    
    if not success:
        return False, results

    # Test completion endpoint
    if verbose:
        print("\n--- Test 2: Basic Completion ---")
    success, message, response = test_completion_endpoint(api_key)
    if verbose:
        print(f"{'✅' if success else '❌'} {message}")
    results.append(f"{'✅' if success else '❌'} Completion endpoint: {message}")
    
    if success and response and verbose:
        print("\nResponse data:")
        print(json.dumps(response, indent=2))
        
        # Extract usage if available
        if "usage" in response:
            usage = response["usage"]
            print("\nToken Usage:")
            print(f"  Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
            print(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}")
            print(f"  Total tokens: {usage.get('total_tokens', 'N/A')}")
    
    return success, results


def check_api_keys(verbose: bool = True) -> List[Dict[str, Any]]:
    """Kiểm tra trạng thái của tất cả OpenRouter API keys trong database"""
    if verbose:
        print("=== OpenRouter API Key Diagnostic ===\n")
    
    results = []
    
    # Get all users
    users = list(users_col().find({}, {"username": 1, "email": 1}))
    if verbose:
        print(f"Found {len(users)} users in database:\n")
    
    for user in users:
        user_id = user["_id"]
        username = user.get("username", "N/A")
        email = user.get("email", "N/A")
        
        if verbose:
            print(f"User: {username} ({email})")
            print(f"  User ID: {user_id}")
        
        # Check for OpenRouter API key
        key_doc = api_keys_col().find_one({"user_id": user_id, "provider": "openrouter"})
        user_result = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "has_key": False,
            "key_status": None,
            "last_used": None,
            "created_at": None
        }
        
        if key_doc:
            api_key = key_doc.get("key_encrypted", "")
            if api_key:
                user_result["has_key"] = True
                user_result["last_used"] = key_doc.get("last_used")
                user_result["created_at"] = key_doc.get("created_at")
                
                # Verify key
                success, messages = verify_openrouter_key(api_key, verbose=False)
                user_result["key_status"] = "valid" if success else "invalid"
                
                if verbose:
                    print(f"  API Key: {mask_key(api_key)}")
                    print(f"  Status: {'✅ Valid' if success else '❌ Invalid'}")
                    if "last_used" in key_doc:
                        print(f"  Last used: {key_doc['last_used']}")
                    if "created_at" in key_doc:
                        print(f"  Created at: {key_doc['created_at']}")
            else:
                if verbose:
                    print("  ❌ API key is empty")
                user_result["key_status"] = "empty"
        else:
            if verbose:
                print("  ❌ No API key found")
            user_result["key_status"] = "missing"
        
        results.append(user_result)
        if verbose:
            print()
            
    return results


if __name__ == "__main__":
    # If run directly, check all keys in database
    check_api_keys()