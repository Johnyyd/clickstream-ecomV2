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
        print("[Spark] Initializing shared Spark session...")
        
        # Set Windows-friendly configurations
        builder = SparkSession.builder \
            .appName("ClickstreamAnalytics") \
            .master("local[*]") \
            .config("spark.driver.memory", "2g") \
            .config("spark.executor.memory", "2g") \
            .config("spark.sql.shuffle.partitions", "8") \
            .config("spark.ui.enabled", "false") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.driver.host", "127.0.0.1")
        
        # Additional Windows compatibility settings
        if os.name == 'nt':  # Windows
            builder = builder \
                .config("spark.sql.warehouse.dir", "file:///C:/tmp/spark-warehouse") \
                .config("spark.local.dir", os.path.join(os.getcwd(), "tmp_spark"))
        
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
