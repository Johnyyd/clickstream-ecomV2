"""
API Configuration Settings
Centralized configuration management with validation and secure defaults.
"""

from typing import List, Dict, Optional, Union

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import validator, Field, SecretStr
import os
import secrets
from pathlib import Path


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = Field("/api/v1", description="API version prefix")
    PROJECT_NAME: str = Field("Clickstream Ecom V2", description="Project name")
    VERSION: str = Field("2.0.0", description="API version")
    DEBUG: bool = Field(False, description="Debug mode")

    # Security Settings
    SECRET_KEY: SecretStr = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT encoding",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        30, ge=1, le=1440, description="Access token expiration in minutes"
    )
    ALGORITHM: str = Field("HS256", description="JWT algorithm")

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "https://app.example.com"],
        description="Allowed CORS origins",
    )
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods",
    )
    CORS_HEADERS: List[str] = Field(default=["*"], description="Allowed HTTP headers")

    # Analysis Engine
    ANALYSIS_ENGINE: str = Field(
        "spark", description="Analysis engine type (spark/pandas)"
    )

    @validator("ANALYSIS_ENGINE")
    def validate_analysis_engine(cls, v):
        if v not in ["spark", "pandas"]:
            raise ValueError("Analysis engine must be either 'spark' or 'pandas'")
        return v

    # MongoDB Settings
    MONGO_URI: str = Field(
        "mongodb://localhost:27017", description="MongoDB connection URI"
    )
    MONGO_DB: str = Field("clickstream", description="MongoDB database name")
    MONGO_MIN_POOL_SIZE: int = Field(
        10, ge=1, description="Minimum connection pool size"
    )
    MONGO_MAX_POOL_SIZE: int = Field(
        100, ge=10, description="Maximum connection pool size"
    )
    MONGO_MAX_IDLE_TIME_MS: int = Field(
        60000, ge=1000, description="Maximum connection idle time (ms)"
    )

    # Spark Settings
    SPARK_MASTER: str = Field("local[*]", description="Spark master URL")
    SPARK_MEMORY: str = Field("6g", description="Spark executor memory")
    SPARK_EXECUTOR_CORES: int = Field(2, ge=1, description="Cores per executor")
    SPARK_EXECUTOR_INSTANCES: int = Field(2, ge=1, description="Number of executors")
    SPARK_CONFIG: Dict[str, str] = Field(
        default={
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            "spark.sql.shuffle.partitions": "200",
            "spark.default.parallelism": "200",
            "spark.streaming.backpressure.enabled": "true",
            "spark.driver.host": "127.0.0.1",
            "spark.driver.bindAddress": "127.0.0.1",
        },
        description="Additional Spark configuration",
    )

    # HDFS Settings
    HDFS_HOST: str = Field("172.19.67.26", description="HDFS namenode host")
    HDFS_PORT: int = Field(9000, ge=1, le=65535, description="HDFS namenode port")
    HDFS_USER: str = Field("hdfs", description="HDFS user")
    HDFS_ROOT_DIR: str = Field(
        "/clickstream", description="HDFS root directory for application"
    )

    # OpenRouter Settings
    OPENROUTER_API_KEY: SecretStr = Field("", description="OpenRouter API key")
    OPENROUTER_TIMEOUT: int = Field(
        30, ge=1, description="OpenRouter API timeout in seconds"
    )

    # Cache Settings
    CACHE_TTL: int = Field(3600, ge=60, description="Cache TTL in seconds")
    CACHE_MAX_SIZE: int = Field(1000, ge=100, description="Maximum cache size")
    CACHE_BACKEND: str = Field(
        "memory", description="Cache backend: 'memory' or 'redis'"
    )
    REDIS_URL: Optional[str] = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL (only used if CACHE_BACKEND='redis')",
    )

    # Logging Settings
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    LOG_FILE: Optional[Path] = Field(None, description="Log file path (optional)")

    # Public debug access key (optional): when set, allows debug endpoints without auth if the provided key matches
    DEBUG_PUBLIC_KEY: Optional[str] = Field(
        default=None,
        description="Optional public key to allow debug=true access without auth",
    )

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()

    def get_mongo_settings(self) -> Dict[str, Union[str, int]]:
        """Get MongoDB connection settings"""
        return {
            "host": self.MONGO_URI,
            "minPoolSize": self.MONGO_MIN_POOL_SIZE,
            "maxPoolSize": self.MONGO_MAX_POOL_SIZE,
            "maxIdleTimeMS": self.MONGO_MAX_IDLE_TIME_MS,
        }

    def get_spark_config(self) -> Dict[str, str]:
        """Get Spark configuration"""
        config = {
            "spark.master": self.SPARK_MASTER,
            "spark.executor.memory": self.SPARK_MEMORY,
            "spark.executor.cores": str(self.SPARK_EXECUTOR_CORES),
            "spark.executor.instances": str(self.SPARK_EXECUTOR_INSTANCES),
        }
        return {**config, **self.SPARK_CONFIG}

    def get_hdfs_url(self) -> str:
        """Get complete HDFS URL"""
        return f"hdfs://{self.HDFS_HOST}:{self.HDFS_PORT}"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

        # Allow environment variables to override
        env_prefix = "CLICKSTREAM_"

        # Custom validation
        validate_all = True
        validate_assignment = True

        # JSON schema generation
        json_schema_extra = {
            "title": "Clickstream Analytics Configuration",
            "description": "Configuration settings for the Clickstream Analytics application",
        }


# Create global settings instance
settings = Settings()
