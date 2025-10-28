"""
API key management service
"""
import time
from typing import Optional

async def validate_api_key(api_key: str) -> bool:
    """
    Validate OpenRouter API key
    """
    if not api_key:
        return False
        
    try:
        # Check key expiration in database
        db_key = await get_api_key(api_key)
        if not db_key:
            return False
            
        # Check if key is expired
        return not is_key_expired(db_key)
    except Exception:
        return False

async def get_api_key(api_key: str) -> Optional[dict]:
    """
    Get API key details from database
    """
    # Implementation depends on your database setup
    pass

def is_key_expired(key_data: dict) -> bool:
    """
    Check if API key is expired
    """
    expiry = key_data.get("expires_at", 0)
    return expiry <= time.time()