"""
Database error handling decorators
"""
import functools
from typing import Any, Callable
import motor.motor_asyncio
import asyncio
from app.core.errors import DatabaseError
from app.core.logging import logger

def handle_db_errors(func: Callable) -> Callable:
    """
    Decorator to handle database errors
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except motor.motor_asyncio.ConnectionFailure as e:
            logger.error(f"Database connection error: {str(e)}")
            raise DatabaseError(
                message="Could not connect to database",
                details={"original_error": str(e)}
            )
        except motor.motor_asyncio.OperationFailure as e:
            logger.error(f"Database operation error: {str(e)}")
            raise DatabaseError(
                message="Database operation failed",
                details={"original_error": str(e)}
            )
        except Exception as e:
            logger.exception("Unexpected database error")
            raise DatabaseError(
                message="An unexpected database error occurred",
                details={"original_error": str(e)}
            )
    return wrapper

def retry_on_error(retries: int = 3, delay: float = 0.1) -> Callable:
    """
    Decorator to retry database operations on failure
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < retries - 1:
                        logger.warning(
                            f"Retrying operation after error: {str(e)}",
                            extra={"attempt": attempt + 1}
                        )
                        await asyncio.sleep(delay * (attempt + 1))
                    continue
            
            logger.error(
                f"Operation failed after {retries} retries",
                extra={"last_error": str(last_error)}
            )
            raise last_error
        return wrapper
    return decorator