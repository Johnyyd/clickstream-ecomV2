"""
Spark Session Manager
Provides optimized Spark configuration and session management
"""
from functools import lru_cache
from typing import Optional
import logging
from pyspark.sql import SparkSession

from app.core.config import SparkConfig

logger = logging.getLogger(__name__)

class SparkManager:
    """Centralized Spark session management"""
    
    def __init__(self):
        self.config = SparkConfig()
        self._session: Optional[SparkSession] = None

    @property
    def session(self) -> SparkSession:
        """Get or create optimized Spark session"""
        if not self._session:
            try:
                # Build session with optimized config
                builder = SparkSession.builder
                for key, value in self.config.get_config().items():
                    builder = builder.config(key, value)
                
                self._session = builder.getOrCreate()
                logger.info("Created new Spark session with optimized configuration")
                
            except Exception as e:
                logger.error(f"Failed to create Spark session: {e}")
                raise
                
        return self._session

    @lru_cache(maxsize=1)
    def get_session(self) -> SparkSession:
        """Cached access to Spark session"""
        return self.session

    def stop(self):
        """Stop Spark session"""
        if self._session:
            self._session.stop()
            self._session = None
            logger.info("Stopped Spark session")

# Global Spark manager instance            
spark_manager = SparkManager()