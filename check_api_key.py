#!/usr/bin/env python3
"""
Diagnostic script to check OpenRouter API key status in the database
"""
from db import api_keys_col, users_col
from bson import ObjectId

def check_api_keys():
    print("=== OpenRouter API Key Diagnostic ===\n")
    
    # Get all users
    users = list(users_col().find({}, {"username": 1, "email": 1}))
    print(f"Found {len(users)} users in database:\n")
    
    for user in users:
        user_id = user["_id"]
        username = user.get("username", "N/A")
        email = user.get("email", "N/A")
        
        print(f"User: {username} ({email})")
        print(f"  User ID: {user_id}")
        
        # Check for OpenRouter API key
        key_doc = api_keys_col().find_one({"user_id": user_id, "provider": "openrouter"})
        
        if key_doc:
            api_key = key_doc.get("key_encrypted", "")
            if api_key:
                # Mask the key (show only last 4 chars)
                masked = ("*" * max(0, len(api_key) - 4)) + api_key[-4:] if len(api_key) > 4 else "****"
                print(f"  ✅ OpenRouter API Key: {masked}")
                print(f"     Key length: {len(api_key)} characters")
                print(f"     Updated: {key_doc.get('updated_at', 'N/A')}")
                
                # Validate key format (OpenRouter keys typically start with "sk-or-")
                if api_key.startswith("sk-or-"):
                    print(f"     Format: ✅ Valid OpenRouter key format")
                else:
                    print(f"     Format: ⚠️  Does not match expected 'sk-or-' prefix")
            else:
                print(f"  ❌ OpenRouter API Key document exists but key is EMPTY")
        else:
            print(f"  ❌ No OpenRouter API Key found")
        
        print()

if __name__ == "__main__":
    check_api_keys()
