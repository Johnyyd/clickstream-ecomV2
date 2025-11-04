"""
Export MongoDB collections to HDFS (Parquet) using shared Spark session & HDFS config
"""
import os
from datetime import datetime, timedelta
from typing import Dict

from pymongo import MongoClient
import pandas as pd
from app.spark.session import get_spark, HDFSConfig


def export_collection_to_hdfs(mongo_collection, hdfs_base_path: str, batch_hours: int = 24):
    now = datetime.utcnow()

    is_time_series = mongo_collection.name in ["events", "sessions"]
    if is_time_series:
        partition_path = f"{hdfs_base_path}/year={now.year}/month={now.month}/day={now.day}/hour={now.hour}"
        query = {"timestamp": {"$gte": int((now - timedelta(hours=batch_hours)).timestamp())}}
    else:
        partition_path = f"{hdfs_base_path}/year={now.year}/month={now.month}/day={now.day}"
        query = {}

    cursor = mongo_collection.find(query)
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return 0

    temp_csv = f"temp_{mongo_collection.name}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        df.to_csv(temp_csv, index=False)
        spark = get_spark()
        sdf = spark.read.csv(temp_csv, header=True, inferSchema=True)
        sdf.repartition(20).write.mode("append").parquet(partition_path)
        return len(df)
    finally:
        try:
            os.remove(temp_csv)
        except Exception:
            pass


def main():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db = os.getenv("MONGO_DB", "clickstream")
    client = MongoClient(mongo_uri)
    db = client[mongo_db]

    base_paths: Dict[str, str] = {
        "events": HDFSConfig.get_path("events"),
        "sessions": HDFSConfig.get_path("sessions"),
        "products": HDFSConfig.get_path("products"),
        "users": HDFSConfig.get_path("users"),
    }

    total = 0
    for name, path in base_paths.items():
        print(f"Exporting {name} -> {path}")
        count = export_collection_to_hdfs(db[name], path)
        print(f"Exported {count} records")
        total += count

    spark = get_spark()
    spark.stop()
    client.close()
    print(f"Done. Total exported: {total}")


if __name__ == "__main__":
    main()
