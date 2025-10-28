"""
Base configuration settings for the application
"""
from typing import List, Dict, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import validator, Field, SecretStr
import os
import secrets
from pathlib import Path

class Settings(BaseSettings):
    """Base settings with common functionality and validation"""
    
    model_config = {
        "title": "Clickstream Analytics Configuration",
        "description": "Configuration settings for the Clickstream Analytics application",
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "str_strip_whitespace": True,
        "validate_default": True,
        "env_prefix": "CLICKSTREAM_",
        "validate_assignment": True,
        "extra": "ignore"
    }
    
    # API Settings
    API_V1_STR: str = Field("/api/v1", description="API version prefix")
    PROJECT_NAME: str = Field("Clickstream Ecom V2", description="Project name")
    VERSION: str = Field("2.0.0", description="API version")
    DEBUG: bool = Field(False, description="Debug mode")
    
    # Security Settings
    SECRET_KEY: SecretStr = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT encoding"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        30, ge=1, le=1440,
        description="Access token expiration in minutes" 
    )
    ALGORITHM: str = Field("HS256", description="JWT algorithm")

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://app.example.com"],
        description="Allowed CORS origins"
    )
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods"
    )
    CORS_HEADERS: List[str] = Field(
        default=["*"],
        description="Allowed HTTP headers"
    )

    # Analysis Engine
    ANALYSIS_ENGINE: str = Field(
        "spark",
        description="Analysis engine type (spark/pandas)"
    )
    
    # Application Description
    DESCRIPTION: str = Field(
        "Clickstream Analytics API for E-commerce",
        description="API description"
    )
    
    # Logging Settings
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_TO_FILE: bool = Field(False, description="Enable file logging")

    @validator("ANALYSIS_ENGINE")
    def validate_analysis_engine(cls, v):
        if v not in ["spark", "pandas"]:
            raise ValueError("Analysis engine must be either 'spark' or 'pandas'")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "str_strip_whitespace": True,
        "validate_default": True,  # Replaces validate_all
        "env_prefix": "CLICKSTREAM_",  # Environment variable prefix
        "validate_assignment": True,  # Validate after model creation
        "extra": "ignore"  # Ignore extra fields for flexibility
    }
        # End of settings class

# Create global settings instance
settings = Settings()