"""
Application Core Components
Provides centralized access to core functionality
"""
from .config import settings
from .database import db_manager
from .spark import spark_manager  
from .openrouter import openrouter_client
from .logging import log_manager

__all__ = [
    'settings',
    'db_manager',
    'spark_manager',
    'openrouter_client',
    'log_manager'
]