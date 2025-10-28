"""
Export MongoDB collections to HDFS in optimized Parquet format.
This script should be run periodically to sync data to HDFS.
"""
from pymongo import MongoClient
import pandas as pd
from pyspark.sql import SparkSession
from datetime import datetime, timedelta
import os

def get_spark():
    return (SparkSession.builder
            .appName("MongoDB to HDFS Export")
            .config("spark.sql.parquet.compression.codec", "snappy")
            .getOrCreate())

def export_collection_to_hdfs(mongo_collection, hdfs_path, spark, batch_size=10000):
    """Export a MongoDB collection to HDFS in optimized Parquet format with clickstream-specific optimizations"""
    
    # Get timestamp for partitioning
    current_time = datetime.now()
    
    # For events and sessions, partition by time
    is_time_series = mongo_collection.name in ['events', 'sessions']
    
    if is_time_series:
        # For time-series data, create hourly partitions for better query performance
        partition_path = f"{hdfs_path}/year={current_time.year}/month={current_time.month}/day={current_time.day}/hour={current_time.hour}"
    else:
        # For dimension tables (users, products), simple daily partitions
        partition_path = f"{hdfs_path}/year={current_time.year}/month={current_time.month}/day={current_time.day}"
    
    # Create temp directory for CSV export with collection-specific name
    temp_csv = f"temp_{mongo_collection.name}_{current_time.strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        # Export MongoDB to CSV in batches with specific query optimization
        query = {}
        if is_time_series:
            # For events/sessions, only export recent data
            last_24h = current_time - timedelta(hours=24)
            query = {
                "timestamp": {"$gte": int(last_24h.timestamp())}
            }
        
        # Fetch data in batches
        cursor = mongo_collection.find(query)
        df_chunks = pd.DataFrame(list(cursor))
        
        if not df_chunks.empty:
            # Save to temp CSV
            df_chunks.to_csv(temp_csv, index=False)
            
            # Read with Spark and write to HDFS as Parquet
            spark_df = spark.read.csv(temp_csv, header=True, inferSchema=True)
            
            # Write directly into the computed partition_path directory
            # This avoids requiring explicit 'year','month','day' columns in the DataFrame schema
            dest_path = partition_path
            spark_df.repartition(20).write.mode("append").parquet(dest_path)
            
            print(f"Successfully exported {df_chunks.shape[0]} records to {dest_path}")
            
    finally:
        # Cleanup temp file
        if os.path.exists(temp_csv):
            os.remove(temp_csv)

def main():
    # Initialize connections
    mongo_client = MongoClient('mongodb://localhost:27017')
    db = mongo_client.clickstream
    spark = get_spark()
    
    # HDFS paths
    hdfs_base = "hdfs://172.19.67.26:9000/user/clickstream"
    collections = {
        "events": f"{hdfs_base}/events",
        "sessions": f"{hdfs_base}/sessions",
        "products": f"{hdfs_base}/products",
        "users": f"{hdfs_base}/users"
    }
    
    # Export each collection
    for coll_name, hdfs_path in collections.items():
        print(f"Exporting {coll_name}...")
        export_collection_to_hdfs(
            mongo_collection=db[coll_name],
            hdfs_path=hdfs_path,
            spark=spark
        )
    
    spark.stop()

if __name__ == "__main__":
    main()