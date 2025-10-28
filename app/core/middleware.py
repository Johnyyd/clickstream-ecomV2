"""
Error handling middleware
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from typing import Dict, Any

from app.core.errors import APIError
from app.core.logging import logger

async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global error handler for all exceptions
    """
    if isinstance(exc, APIError):
        # Handle our custom exceptions
        error_response = {
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
        logger.error(
            f"API Error: {exc.error_code}",
            extra={
                "path": request.url.path,
                "details": exc.details,
                "status_code": exc.status_code
            }
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    elif isinstance(exc, PydanticValidationError):
        # Handle Pydantic validation errors
        error_response = {
            "error": "VALIDATION_ERROR",
            "message": "Invalid request data",
            "details": {
                "errors": [
                    {
                        "loc": err["loc"],
                        "msg": err["msg"],
                        "type": err["type"]
                    }
                    for err in exc.errors()
                ]
            }
        }
        logger.warning(
            "Validation Error",
            extra={
                "path": request.url.path,
                "details": error_response["details"]
            }
        )
        return JSONResponse(
            status_code=400,
            content=error_response
        )
    
    else:
        # Handle unexpected errors
        error_response = {
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred"
        }
        
        # Log full error details
        logger.exception(
            "Unexpected Error",
            extra={
                "path": request.url.path,
                "error_type": type(exc).__name__
            }
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )

def setup_error_handlers(app):
    """
    Configure error handlers for FastAPI app
    """
    app.middleware("http")(error_logging_middleware)
    app.exception_handler(Exception)(error_handler)

async def error_logging_middleware(request: Request, call_next):
    """
    Middleware for logging all errors
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.exception(
            "Unhandled Exception",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__
            }
        )
        raise