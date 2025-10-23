"""
Spark Performance Monitoring and Optimization Utilities
"""
import time
import functools
from typing import Callable, Any


def monitor_performance(func: Callable) -> Callable:
    """
    Decorator to monitor Spark job performance.
    Prints execution time and memory usage.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"\n{'='*60}")
        print(f"🚀 Starting: {func.__name__}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n{'='*60}")
            print(f"✅ Completed: {func.__name__}")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n{'='*60}")
            print(f"❌ Failed: {func.__name__}")
            print(f"⏱️  Duration before failure: {duration:.2f}s")
            print(f"🔴 Error: {str(e)}")
            print(f"{'='*60}\n")
            
            raise
    
    return wrapper


def get_spark_metrics(spark):
    """
    Get current Spark session metrics.
    
    Returns dict with:
    - active_jobs: Number of active jobs
    - cached_tables: Number of cached tables
    - storage_memory: Storage memory used
    """
    try:
        sc = spark.sparkContext
        status = sc.statusTracker()
        
        metrics = {
            "active_jobs": len(status.getActiveJobIds()),
            "active_stages": len(status.getActiveStageIds()),
        }
        
        # Try to get cached tables
        try:
            cached_tables = [t for t in spark.catalog.listTables() if t.isTemporary]
            metrics["cached_tables"] = len(cached_tables)
        except:
            metrics["cached_tables"] = 0
        
        return metrics
        
    except Exception as e:
        print(f"Warning: Could not get Spark metrics: {e}")
        return {}


def print_dataframe_stats(df, name="DataFrame"):
    """
    Print useful statistics about a DataFrame.
    """
    try:
        print(f"\n📊 Stats for {name}:")
        print(f"   Partitions: {df.rdd.getNumPartitions()}")
        
        # Get storage level
        storage_level = df.storageLevel
        if storage_level.useMemory or storage_level.useDisk:
            print(f"   Cached: Yes ({storage_level})")
        else:
            print(f"   Cached: No")
        
        print()
        
    except Exception as e:
        print(f"Warning: Could not get DataFrame stats: {e}")


def optimize_query_plan(df):
    """
    Print query execution plan for optimization analysis.
    """
    try:
        print("\n🔍 Query Plan (Optimized):")
        df.explain(mode="formatted")
        print()
    except Exception as e:
        print(f"Warning: Could not show query plan: {e}")


class SparkTimer:
    """
    Context manager for timing Spark operations.
    
    Usage:
        with SparkTimer("Load data"):
            df = spark.read.csv(...)
    """
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        print(f"▶️  {self.operation_name}...")
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            print(f"✅ {self.operation_name} completed in {duration:.2f}s")
        else:
            print(f"❌ {self.operation_name} failed after {duration:.2f}s")
        
        return False  # Don't suppress exceptions


def batch_process(items, batch_size=1000):
    """
    Generator to process items in batches.
    Useful for large datasets to avoid memory issues.
    
    Usage:
        for batch in batch_process(large_list, batch_size=500):
            # Process batch
            pass
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def estimate_dataframe_size(df, sample_fraction=0.1):
    """
    Estimate DataFrame size in memory.
    
    Args:
        df: Spark DataFrame
        sample_fraction: Fraction to sample (0-1)
    
    Returns:
        dict with estimated_rows and estimated_mb
    """
    try:
        # Sample and count
        sample_count = df.sample(sample_fraction).count()
        estimated_rows = int(sample_count / sample_fraction)
        
        # Very rough estimate: ~100 bytes per row average
        estimated_bytes = estimated_rows * 100
        estimated_mb = estimated_bytes / (1024 * 1024)
        
        return {
            "estimated_rows": estimated_rows,
            "estimated_mb": round(estimated_mb, 2),
            "recommendation": "Cache" if estimated_mb < 1000 else "Process in batches"
        }
        
    except Exception as e:
        print(f"Warning: Could not estimate DataFrame size: {e}")
        return {}
