"""
API Dependencies
"""
from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import db_manager
from app.core.spark import spark_manager
from app.core.openrouter import openrouter_client
from app.models.user import User

from .common import AuthError, get_token_header, validate_token
from app.services.auth import get_user_by_token as resolve_user_by_session_token

security = HTTPBearer()
# Optional security that does not auto-reject when Authorization is missing
security_optional = HTTPBearer(auto_error=False)

async def get_db():
    """Get database connection"""
    return db_manager

async def get_spark():
    """Get Spark session"""
    return spark_manager

async def get_openrouter():
    """Get OpenRouter client"""
    return openrouter_client

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user
    
    Raises:
        AuthError if token invalid or user not found
    """
    token = credentials.credentials
    valid, error = validate_token(token)
    
    if not valid:
        raise AuthError(f"Invalid token: {error}")
        
    # Resolve user via session token (stored in sessions collection)
    try:
        user = resolve_user_by_session_token(token)
        if not user:
            raise AuthError("User not found")
        return user
    except Exception as e:
        raise AuthError(f"Error getting user: {e}")
        
async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None"""
    if not credentials:
        return None
        
    try:
        return await get_current_user(request, credentials)
    except AuthError:
        return None

async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """
    Verify API key from Authorization header
    
    Args:
        request: FastAPI request
        credentials: Authorization credentials from Bearer token
        
    Returns:
        bool: True if API key is valid
        
    Raises:
        AuthError: If API key is invalid
    """
    api_key = credentials.credentials
    if not api_key:
        raise AuthError("Missing API key")
    
    try:
        db = await get_db()
        # Verify key exists and is active
        key_valid = await db.api_keys.verify_key(api_key)
        if not key_valid:
            raise AuthError("Invalid API key")
            
        # Update last used timestamp
        await db.api_keys.update_last_used(api_key)
        return True
        
    except Exception as e:
        raise AuthError(f"Error verifying API key: {e}")