"""
Auth API - Legacy compatibility layer
Re-exports auth router from v1 endpoints
"""
from app.api.v1.endpoints.auth import router

__all__ = ["router"]
