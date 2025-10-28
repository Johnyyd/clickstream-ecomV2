"""
API Router Factory
Provides centralized router creation and configuration
"""
from fastapi import APIRouter
from typing import List, Optional

from .endpoints import (
    auth,
    events,
    products,
    analyses,
    analytics,
    openrouter,
    recommendations,
    metrics,
    cart,
    ml
)

def create_router(
    prefix: str = "/api/v1",
    tags: Optional[List[str]] = None,
    include_auth: bool = True
) -> APIRouter:
    """
    Create configured API router with all endpoints
    """
    if tags is None:
        tags = ["api"]
        
    router = APIRouter(prefix=prefix, tags=tags)
    
    # Core endpoints
    router.include_router(events.router, prefix="/events", tags=["events"])
    router.include_router(products.router, prefix="/products", tags=["products"])
    router.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
    
    # Analytics endpoints
    router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
    router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
    router.include_router(ml.router, prefix="/ml", tags=["ml"])
    
    # Feature endpoints
    router.include_router(cart.router, prefix="/cart", tags=["cart"])
    router.include_router(
        recommendations.router, 
        prefix="/recommendations",
        tags=["recommendations"]
    )
    
    # Integration endpoints
    router.include_router(
        openrouter.router,
        prefix="/openrouter",
        tags=["openrouter"]
    )
    
    # Auth endpoints (optional)
    if include_auth:
        router.include_router(auth.router, prefix="/auth", tags=["auth"])
    
    return router

# Create default API router instance for export
api_router = create_router()

def create_router(
    prefix: str = "/api/v1",
    tags: Optional[List[str]] = None,
    include_auth: bool = True
) -> APIRouter:
    """
    Create configured API router with all endpoints
    
    Args:
        prefix: API route prefix
        tags: OpenAPI tags
        include_auth: Whether to include auth endpoints
        
    Returns:
        Configured APIRouter instance
    """
    if tags is None:
        tags = ["api"]
        
    router = APIRouter(prefix=prefix, tags=tags)
    
    # Core endpoints
    router.include_router(events.router, prefix="/events", tags=["events"])
    router.include_router(products.router, prefix="/products", tags=["products"])
    router.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
    
    # Analytics endpoints
    router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
    router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
    router.include_router(ml.router, prefix="/ml", tags=["ml"])
    
    # Feature endpoints
    router.include_router(cart.router, prefix="/cart", tags=["cart"])
    router.include_router(
        recommendations.router, 
        prefix="/recommendations",
        tags=["recommendations"]
    )
    
    # Integration endpoints
    router.include_router(
        openrouter.router,
        prefix="/openrouter",
        tags=["openrouter"]
    )
    
    # Auth endpoints (optional)
    if include_auth:
        router.include_router(auth.router, prefix="/auth", tags=["auth"])
    
    return router