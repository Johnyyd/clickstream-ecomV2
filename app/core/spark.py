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

# Backward-compatible helpers expected by spark modules
def create_spark_session(app_name: str | None = None):
    """Return a SparkSession. If app_name is provided and a session doesn't exist yet,
    it will be used when creating the session. If a session already exists, we return it as-is.
    """
    # If no session yet and app_name provided, prime builder via accessing property once
    if not getattr(spark_manager, "_session", None):
        try:
            # Build with config and optionally app name
            builder = SparkSession.builder
            for key, value in spark_manager.config.get_config().items():
                builder = builder.config(key, value)
            if app_name:
                builder = builder.appName(app_name)
            spark_manager._session = builder.getOrCreate()
            logger.info("Created Spark session%s", f" (appName={app_name})" if app_name else "")
        except Exception as e:
            logger.error(f"Failed to create Spark session: {e}")
            raise
    return spark_manager.get_session()


def optimize_spark_df(df):
    """Lightweight dataframe optimization helper used by analytics modules.
    Safe no-op if not applicable.
    """
    try:
        # Common light optimizations
        df = df.cache()
        # Avoid many small partitions for local dev
        try:
            num_parts = df.rdd.getNumPartitions()
            if num_parts and num_parts > 8:
                df = df.coalesce(8)
        except Exception:
            pass
        return df
    except Exception:
        return df