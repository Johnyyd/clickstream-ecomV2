from db import users_col, api_keys_col
from auth import hash_password
from datetime import datetime
from bson import ObjectId

def setup_test_user():
    # Create test user
    user = {
        "_id": ObjectId(),
        "username": "test_user",
        "email": "test@example.com",
        "password_hash": hash_password("test123"),
        "role": "user",
        "created_at": datetime.utcnow()
    }
    
    # Check if user exists
    existing = users_col().find_one({"username": "test_user"})
    if existing:
        print("Test user already exists")
        return existing
    
    result = users_col().insert_one(user)
    print(f"Created test user with ID: {result.inserted_id}")
    
    # Add API key
    api_key = {
        "user_id": result.inserted_id,
        "provider": "openrouter",
        "key_encrypted": "test_key",  # In production, this should be properly encrypted
        "created_at": datetime.utcnow()
    }
    
    key_result = api_keys_col().insert_one(api_key)
    print(f"Added API key with ID: {key_result.inserted_id}")
    
    return user

if __name__ == "__main__":
    print("\n=== Setting up test data ===")
    user = setup_test_user()
    print("\nTest user credentials:")
    print("Username: test_user")
    print("Password: test123")
    print("\nYou can now login with these credentials on the dashboard.")