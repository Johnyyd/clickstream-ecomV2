from app.core.db_sync import users_col, api_keys_col
from app.services.auth import hash_password
from datetime import datetime
from bson import ObjectId
import pytz
def setup_test_user():
    # Create test user
    user = {
        "_id": ObjectId(),
        "username": "admin",
        "email": "admin@example.com",
        "password_hash": hash_password("admin123"),
        "role": "admin",
        "created_at": datetime.now(pytz.UTC)
    }
    
    # Check if user exists
    existing = users_col().find_one({"username": "admin"})
    if existing:
        print("Test user already exists")
        return existing
    
    result = users_col().insert_one(user)
    print(f"Created test user with ID: {result.inserted_id}")
    
    # Add API key
    api_key = {
        "user_id": result.inserted_id,
        "provider": "openrouter",
        "key": "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",  # In production, this should be properly encrypted
        "created_at": datetime.now(pytz.UTC)
    }
    
    key_result = api_keys_col().insert_one(api_key)
    print(f"Added API key with ID: {key_result.inserted_id}")
    
    return user

if __name__ == "__main__":
    print("\n=== Setting up test data ===")
    user = setup_test_user()
    print("\nTest user credentials:")
    print("Username: admin")
    print("Password: admin123")
    print("\nYou can now login with these credentials on the dashboard.")