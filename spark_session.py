"""
Centralized Spark Session Manager
Provides a single shared Spark session for all analytics modules
"""
import os
import sys
from typing import Optional

# Configure Java/Spark environment BEFORE importing PySpark
if "JAVA_HOME" not in os.environ:
    os.environ["JAVA_HOME"] = r"C:\LUUDULIEU\APP\JDK\jdk-17.0.12"

os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
python_exe = sys.executable
os.environ["PYSPARK_PYTHON"] = python_exe
os.environ["PYSPARK_DRIVER_PYTHON"] = python_exe

from pyspark.sql import SparkSession

# Global singleton Spark session
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
