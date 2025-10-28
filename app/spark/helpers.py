"""
Spark Helper Functions
Provides utility functions for Spark operations
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from pyspark.sql import DataFrame
from pyspark.sql.functions import col
from app.spark.session import get_spark, HDFSConfig

logger = logging.getLogger(__name__)

def write_hdfs_data(
    df: DataFrame,
    collection: str,
    mode: str = "append",
    partition_cols: Optional[list] = None
) -> None:
    """
    Write DataFrame to HDFS with optimized partitioning
    
    Args:
        df: Spark DataFrame to write
        collection: Target collection name
        mode: Write mode ('append', 'overwrite', etc)
        partition_cols: Optional columns to partition by
    """
    try:
        # Get base path for the collection
        base_path = HDFSConfig.get_path(collection)
        
        # Set up the writer
        writer = df.write.format("parquet").mode(mode)
        
        # Add partitioning if specified
        if partition_cols:
            writer = writer.partitionBy(*partition_cols)
        
        # Write with optimized settings
        (writer
         .option("compression", "snappy")
         .option("spark.sql.files.maxRecordsPerFile", "1000000")
         .save(base_path))
        
        logger.info(f"Successfully wrote data to {base_path}")
        
    except Exception as e:
        logger.error(f"Error writing to HDFS: {str(e)}")
        raise

def optimize_hdfs_data(
    collection: str,
    vacuum_retention: str = "7 days"
) -> None:
    """
    Optimize HDFS data storage
    
    Args:
        collection: Collection to optimize
        vacuum_retention: Retention period for vacuum
    """
    try:
        spark = get_spark()
        path = HDFSConfig.get_path(collection)
        
        # Optimize file size and layout
        spark.sql(f"OPTIMIZE '{path}'")
        
        # Clean up old files
        spark.sql(f"VACUUM '{path}' RETAIN {vacuum_retention}")
        
        logger.info(f"Successfully optimized {collection} data")
        
    except Exception as e:
        logger.error(f"Error optimizing HDFS data: {str(e)}")
        raise

def cache_collection(
    collection: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> DataFrame:
    """
    Cache frequently accessed data in memory
    
    Args:
        collection: Collection to cache
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
    
    Returns:
        DataFrame: Cached Spark DataFrame
    """
    try:
        from app.spark.session import read_hdfs_data
        df = read_hdfs_data(collection, start_date, end_date)
        
        # Cache with compression
        df.persist(storageLevel="MEMORY_AND_DISK_SER")
        
        # Force cache loading
        df.count()
        
        logger.info(f"Successfully cached {collection} data")
        return df
        
    except Exception as e:
        logger.error(f"Error caching data: {str(e)}")
        raise

def get_session_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Calculate key session metrics
    
    Args:
        start_date: Optional start date
        end_date: Optional end date
    
    Returns:
        Dict with metrics
    """
    try:
        from app.spark.session import read_hdfs_data
        df = read_hdfs_data("sessions", start_date, end_date)
        
        metrics = {
            "total_sessions": df.count(),
            "avg_session_length": df.agg({"event_count": "avg"}).collect()[0][0],
            "bounce_rate": df.filter(col("event_count") == 1).count() / df.count()
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating session metrics: {str(e)}")
        raise