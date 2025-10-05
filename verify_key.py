#!/usr/bin/env python3
"""
Script để verify OpenRouter API key
"""
import requests
import json

def verify_openrouter_key(api_key):
    """Verify OpenRouter API key bằng cách gọi models endpoint"""
    print("=" * 60)
    print("OPENROUTER API KEY VERIFICATION")
    print("=" * 60)
    
    # Mask key for display
    masked = ("*" * max(0, len(api_key) - 4)) + api_key[-4:] if len(api_key) > 4 else "****"
    print(f"\nTesting key: {masked}")
    print(f"Key length: {len(api_key)} characters")
    
    # Check format
    if not api_key.startswith("sk-or-"):
        print("❌ Invalid key format! OpenRouter keys should start with 'sk-or-'")
        return False
    else:
        print("✅ Key format is correct")
    
    # Test 1: List models endpoint (doesn't require credits)
    print("\n--- Test 1: List Models ---")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Clickstream Dashboard"
            },
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Key is valid! Can list models.")
            data = response.json()
            print(f"   Found {len(data.get('data', []))} models")
        elif response.status_code == 401:
            print("❌ Key is INVALID or EXPIRED!")
            print(f"   Response: {response.text}")
            return False
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Check credits
    print("\n--- Test 2: Check Credits ---")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Key info retrieved:")
            print(f"   Label: {data.get('data', {}).get('label', 'N/A')}")
            print(f"   Usage: ${data.get('data', {}).get('usage', 0):.4f}")
            print(f"   Limit: ${data.get('data', {}).get('limit', 'unlimited')}")
            
            # Check if limit reached
            usage = data.get('data', {}).get('usage', 0)
            limit = data.get('data', {}).get('limit')
            
            if limit and usage >= limit:
                print("⚠️  WARNING: Usage limit reached!")
                return False
        else:
            print(f"⚠️  Could not retrieve key info: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️  Could not check credits: {e}")
    
    # Test 3: Try a simple completion
    print("\n--- Test 3: Test Completion ---")
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Clickstream Dashboard"
            },
            json={
                "model": "z-ai/glm-4.5-air:free",
                "messages": [
                    {"role": "user", "content": "Say 'test' in JSON format"}
                ],
                "max_tokens": 50
            },
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Completion successful!")
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"   Response: {content[:100]}...")
            return True
        elif response.status_code == 401:
            print("❌ Unauthorized! Key is invalid or expired.")
            print(f"   Response: {response.text}")
            return False
        elif response.status_code == 402:
            print("❌ Payment required! Out of credits.")
            print(f"   Response: {response.text}")
            return False
        elif response.status_code == 429:
            print("⚠️  Rate limited. Try again later.")
            return False
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


def main():
    # Try to load key from key.txt
    try:
        with open("key.txt", "r") as f:
            api_key = f.read().strip()
    except Exception as e:
        print(f"❌ Could not read key.txt: {e}")
        print("\nPlease create key.txt with your OpenRouter API key")
        return
    
    if not api_key:
        print("❌ key.txt is empty!")
        return
    
    # Verify the key
    is_valid = verify_openrouter_key(api_key)
    
    print("\n" + "=" * 60)
    if is_valid:
        print("✅ KEY IS VALID AND WORKING!")
        print("=" * 60)
        print("\nYou can now use this key in your application.")
        print("The key will be automatically loaded from key.txt")
    else:
        print("❌ KEY IS NOT WORKING!")
        print("=" * 60)
        print("\nPossible solutions:")
        print("1. Get a new key from https://openrouter.ai/keys")
        print("2. Check if you have credits in your account")
        print("3. Make sure the key hasn't been revoked")
        print("4. Try using a different model (some are free)")
    print()


if __name__ == "__main__":
    main()
