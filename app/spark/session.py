"""
Centralized Spark Session Manager
Provides optimized Spark configuration for clickstream analytics with HDFS integration
"""
import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Configuration
JAVA_HOME = os.environ.get("JAVA_HOME", r"C:\LUUDULIEU\APP\JDK\jdk-17.0.12")
SPARK_LOCAL_IP = os.environ.get("SPARK_LOCAL_IP", "127.0.0.1")
SPARK_MEMORY = os.environ.get("SPARK_MEMORY", "6g")
SPARK_PARALLELISM = os.environ.get("SPARK_PARALLELISM", "100")

# Configure environment
os.environ["JAVA_HOME"] = JAVA_HOME
os.environ["SPARK_LOCAL_IP"] = SPARK_LOCAL_IP
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, window

# HDFS Configuration
class HDFSConfig:
    BASE = os.environ.get("HDFS_BASE", "hdfs://172.19.67.26:9000/user/clickstream")
    PATHS = {
        "events": f"{BASE}/events",
        "sessions": f"{BASE}/sessions",
        "products": f"{BASE}/products",
        "users": f"{BASE}/users"
    }
    
    @staticmethod
    def get_path(collection: str, dt: Optional[datetime] = None) -> str:
        """Get HDFS path with optional date partitioning"""
        base = HDFSConfig.PATHS.get(collection)
        if not base:
            raise ValueError(f"Unknown collection: {collection}")
            
        if dt and collection in ["events", "sessions"]:
            return f"{base}/year={dt.year}/month={dt.month}/day={dt.day}/hour={dt.hour}"
        return base

# Spark Configuration
class SparkConfig:
    MEMORY = SPARK_MEMORY
    PARALLELISM = SPARK_PARALLELISM
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get optimized Spark configuration"""
        return {
            # Memory Configuration
            "spark.executor.memory": SparkConfig.MEMORY,
            "spark.driver.memory": SparkConfig.MEMORY,
            "spark.memory.offHeap.enabled": "true",
            "spark.memory.offHeap.size": "2g",
            
            # Performance Optimization
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            "spark.sql.adaptive.localShuffleReader.enabled": "true",
            "spark.sql.adaptive.skewJoin.enabled": "true",
            
            # Storage & Caching
            "spark.sql.inMemoryColumnarStorage.compressed": "true",
            "spark.sql.inMemoryColumnarStorage.batchSize": "20000",
            "spark.sql.files.maxPartitionBytes": "128m",
            "spark.sql.shuffle.partitions": SparkConfig.PARALLELISM,
            
            # Broadcast & Join Optimization
            "spark.sql.autoBroadcastJoinThreshold": "100m",
            "spark.sql.shuffle.targetPostShuffleInputSize": "128m",
            
            # Other Settings
            "spark.sql.warehouse.dir": "spark-warehouse",
            "spark.sql.session.timeZone": "UTC",
            "spark.default.parallelism": SparkConfig.PARALLELISM
        }

# Global singleton Spark session
_spark: Optional[SparkSession] = None

@lru_cache(maxsize=1)
def get_spark() -> SparkSession:
    """Get or create the global Spark session with optimized configuration"""
    global _spark
    if not _spark:
        try:
            builder = SparkSession.builder.appName("Clickstream Analytics")
            
            # Apply all configurations
            for key, value in SparkConfig.get_config().items():
                builder = builder.config(key, value)
            
            _spark = builder.getOrCreate()
            logger.info("Successfully created Spark session with optimized config")
            
        except Exception as e:
            logger.error(f"Failed to create Spark session: {str(e)}")
            raise# Global singleton Spark session
_spark: Optional[SparkSession] = None

def get_spark() -> SparkSession:
    """Get or create the global Spark session optimized for clickstream analytics"""
    global _spark
    if not _spark:
        _spark = (SparkSession.builder
                 .appName("Clickstream Analytics")
                 # Memory configuration
                 .config("spark.sql.warehouse.dir", "spark-warehouse")
                 .config("spark.executor.memory", "6g")  # Increased for complex clickstream analysis
                 .config("spark.driver.memory", "6g")
                 .config("spark.memory.offHeap.enabled", "true")
                 .config("spark.memory.offHeap.size", "2g")
                 
                 # Performance optimizations
                 .config("spark.sql.adaptive.enabled", "true")
                 .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
                 .config("spark.sql.adaptive.localShuffleReader.enabled", "true")
                 .config("spark.sql.adaptive.skewJoin.enabled", "true")
                 
                 # Caching and shuffling optimizations
                 .config("spark.sql.inMemoryColumnarStorage.compressed", "true")
                 .config("spark.sql.inMemoryColumnarStorage.batchSize", "20000")
                 .config("spark.sql.shuffle.partitions", "200")  # Adjust based on data volume
                 .config("spark.sql.autoBroadcastJoinThreshold", "100m")
                 
                 # IO optimizations
                 .config("spark.sql.parquet.compression.codec", "snappy")
                 .config("spark.sql.files.maxPartitionBytes", "128m")
                 .config("spark.sql.files.openCostInBytes", "32m")
                 
                 # Specific for clickstream analysis
                 .config("spark.sql.session.timeZone", "UTC")
                 .config("spark.sql.shuffle.targetPostShuffleInputSize", "128m")
                 .config("spark.default.parallelism", "100")  # Adjust based on cluster
                 .getOrCreate())
    return _spark

def read_hdfs_data(
    collection: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    columns: Optional[list] = None
) -> DataFrame:
    """
    Read data from HDFS with optimized filtering and column selection
    
    Args:
        collection: The collection to read ('events', 'sessions', etc)
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        columns: Optional list of columns to select (improves performance)
    
    Returns:
        DataFrame: Spark DataFrame with the requested data
    """
    try:
        spark = get_spark()
        base_path = HDFSConfig.get_path(collection)
        
        # Build the read operation
        reader = spark.read.format("parquet")
        
        # Select specific columns if provided
        if columns:
            reader = reader.select(*columns)
            
        # Read the data
        df = reader.load(base_path)
        
        # Apply date filtering if provided
        if start_date and end_date:
            df = df.filter(
                (col("year") >= start_date.year) & 
                (col("month") >= start_date.month) & 
                (col("day") >= start_date.day) &
                (col("year") <= end_date.year) &
                (col("month") <= end_date.month) &
                (col("day") <= end_date.day)
            )
            
            # For time-series collections, add hour filtering
            if collection in ["events", "sessions"]:
                df = df.filter(
                    (col("hour") >= start_date.hour if start_date else True) &
                    (col("hour") <= end_date.hour if end_date else True)
                )
        
        return df
        
    except Exception as e:
        logger.error(f"Error reading from HDFS: {str(e)}")
        raise
_spark_session: Optional[SparkSession] = None


def get_spark_session() -> Optional[SparkSession]:
    """
    Get or create a singleton Spark session.
    Returns None if Spark cannot be initialized (graceful degradation).
    """
    global _spark_session
    
    # Return existing session if available
    if _spark_session is not None:
        try:
            # Verify session is still active
            _spark_session.sparkContext.getConf()
            return _spark_session
        except Exception:
            # Session died, will recreate
            _spark_session = None
    
    # Try to create new session
    try:
        print("[Spark] Initializing optimized shared Spark session...")
        
        # Java 17 compatibility - Add JVM options for module access
        java_17_options = [
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED",
            "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
            "--add-opens=java.base/java.io=ALL-UNNAMED",
            "--add-opens=java.base/java.net=ALL-UNNAMED",
            "--add-opens=java.base/java.nio=ALL-UNNAMED",
            "--add-opens=java.base/java.util=ALL-UNNAMED",
            "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED",
            "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED",
            "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
            "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
            "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED",
            "--add-opens=java.security.jgss/sun.security.krb5=ALL-UNNAMED"
        ]
        java_options = " ".join(java_17_options)
        
        # Performance-optimized configurations
        builder = SparkSession.builder \
            .appName("ClickstreamAnalytics") \
            .master("local[*]") \
            .config("spark.driver.memory", "4g") \
            .config("spark.executor.memory", "4g") \
            .config("spark.memory.fraction", "0.8") \
            .config("spark.memory.storageFraction", "0.3") \
            .config("spark.sql.shuffle.partitions", "8") \
            .config("spark.default.parallelism", "8") \
            .config("spark.ui.enabled", "false") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.driver.host", "127.0.0.1") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.sql.adaptive.skewJoin.enabled", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .config("spark.kryoserializer.buffer.max", "512m") \
            .config("spark.sql.autoBroadcastJoinThreshold", "10485760") \
            .config("spark.cleaner.periodicGC.interval", "5min") \
            .config("spark.cleaner.referenceTracking.cleanCheckpoints", "true") \
            .config("spark.driver.extraJavaOptions", java_options) \
            .config("spark.executor.extraJavaOptions", java_options)
        
        # Additional Windows compatibility settings
        if os.name == 'nt':  # Windows
            # Use C:/tmp to avoid long path issues
            import tempfile
            spark_tmp_dir = "C:/tmp/spark"
            os.makedirs(spark_tmp_dir, exist_ok=True)
            
            builder = builder \
                .config("spark.sql.warehouse.dir", "file:///C:/tmp/spark-warehouse") \
                .config("spark.local.dir", spark_tmp_dir) \
                .config("spark.shuffle.file.buffer", "1m") \
                .config("spark.unsafe.sorter.spill.reader.buffer.size", "1m") \
                .config("spark.file.transferTo", "false") \
                .config("spark.shuffle.unsafe.file.output.buffer", "1m") \
                .config("spark.io.compression.lz4.blockSize", "512k")
        
        _spark_session = builder.getOrCreate()
        
        # Set log level to reduce noise
        _spark_session.sparkContext.setLogLevel("WARN")
        
        print(f"[Spark] ✅ Session initialized: {_spark_session.version}")
        return _spark_session
        
    except FileNotFoundError as e:
        print(f"[Spark] ⚠️ Spark/Java not found: {e}")
        print("[Spark] Analytics features will be disabled. Install Java 8/11 and set JAVA_HOME to enable.")
        return None
    except Exception as e:
        print(f"[Spark] ⚠️ Failed to initialize Spark: {e}")
        print("[Spark] Analytics features will be disabled.")
        import traceback
        print("[Spark] Full error traceback:")
        traceback.print_exc()
        return None


def stop_spark_session():
    """
    Stop the shared Spark session.
    Call this on application shutdown.
    """
    global _spark_session
    if _spark_session is not None:
        try:
            _spark_session.stop()
            print("[Spark] Session stopped")
        except Exception as e:
            print(f"[Spark] Error stopping session: {e}")
        finally:
            _spark_session = None


def is_spark_available() -> bool:
    """
    Check if Spark is available and working.
    """
    session = get_spark_session()
    return session is not None


def cache_dataframe(df, storage_level="MEMORY_AND_DISK"):
    """
    Cache DataFrame with specified storage level for better performance.
    
    Args:
        df: Spark DataFrame to cache
        storage_level: One of MEMORY_ONLY, MEMORY_AND_DISK, DISK_ONLY
    
    Returns:
        Cached DataFrame
    """
    from pyspark import StorageLevel
    
    level_map = {
        "MEMORY_ONLY": StorageLevel.MEMORY_ONLY,
        "MEMORY_AND_DISK": StorageLevel.MEMORY_AND_DISK,
        "DISK_ONLY": StorageLevel.DISK_ONLY,
        "MEMORY_ONLY_SER": StorageLevel.MEMORY_ONLY_SER,
        "MEMORY_AND_DISK_SER": StorageLevel.MEMORY_AND_DISK_SER
    }
    
    level = level_map.get(storage_level, StorageLevel.MEMORY_AND_DISK)
    return df.persist(level)


def optimize_dataframe(df):
    """
    Apply common optimization techniques to DataFrame.
    
    - Repartition based on size
    - Coalesce if too many small partitions
    - Cache if small enough
    
    Args:
        df: Spark DataFrame
    
    Returns:
        Optimized DataFrame
    """
    try:
        # Count partitions
        num_partitions = df.rdd.getNumPartitions()
        
        # If too many partitions for small data, coalesce
        if num_partitions > 8:
            df = df.coalesce(8)
        
        return df
    except Exception as e:
        print(f"[Spark] Optimization warning: {e}")
        return df
