"""
Common API functionality and utilities
"""
from typing import Optional, Tuple

from fastapi import Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# Auth scheme
security = HTTPBearer()

def get_token_header(
    authorization: Optional[str] = Header(default=None)
) -> Optional[str]:
    """Extract token from Authorization header"""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            return token
    return None

def validate_token(token: str) -> Tuple[bool, Optional[str]]:
    """
    Validate JWT token
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Add token validation logic here
        return True, None
    except Exception as e:
        return False, str(e)
        
class APIError(HTTPException):
    """Base API error"""
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "message": message,
                "error_code": error_code or "unknown_error"
            }
        )
        
class AuthError(APIError):
    """Authentication error"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            error_code="auth_error"
        )
        
class NotFoundError(APIError):
    """Resource not found error"""
    def __init__(self, resource: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"{resource} not found",
            error_code="not_found"
        )
        
class ValidationError(APIError):
    """Validation error"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            error_code="validation_error"
        )