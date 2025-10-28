"""
API Initialization and Configuration
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional

from app.core.config import settings
from app.core.logging import log_manager
from app.core.database import db_manager

from .router import create_router
from .models import HealthResponse

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Clickstream Analytics API",
        version=settings.VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )
    
    # Create API router
    api_router = create_router()
    app.include_router(api_router)
    
    # Add health check
    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    async def health_check():
        return {
            "status": "ok",
            "version": settings.VERSION,
            "environment": "development" if settings.DEBUG else "production"
        }
    
    # Add startup event
    @app.on_event("startup")
    async def startup():
        # Configure logging
        log_manager.setup_logging()
        
        # Initialize database
        await db_manager.connect()
        await db_manager.create_indexes()
        
    # Add shutdown event  
    @app.on_event("shutdown")
    async def shutdown():
        await db_manager.close()
        
    return app

# Create app instance
app = create_app()