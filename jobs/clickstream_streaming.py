from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, MapType
import os
import pytz
from pymongo import MongoClient
from datetime import datetime

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "clickstream.events")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "clickstream")

# Inner event schema (flat fields)
event_schema = StructType([
    StructField("session_id", StringType()),
    StructField("user_id", StringType()),
    StructField("page", StringType()),
    StructField("event_type", StringType()),
    StructField("properties", MapType(StringType(), StringType())),
    StructField("timestamp", DoubleType()),
])

# Outer payload schema: {"event": <event_schema>, "metadata": {...}}
outer_schema = StructType([
    StructField("event", event_schema),
    StructField("metadata", MapType(StringType(), StringType())),
])

def _write_mongo(df, epoch_id):
    records = [
        {
            "window_start": r["window_start"],
            "window_end": r["window_end"],
            "page": r["page"],
            "event_type": r["event_type"],
            "count": int(r["count"]),
            "updated_at": datetime.now(pytz.utc),
        }
        for r in df.collect()
    ]
    if not records:
        return
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    col = db["aggregates_minute"]
    for rec in records:
        col.update_one(
            {
                "window_start": rec["window_start"],
                "window_end": rec["window_end"],
                "page": rec["page"],
                "event_type": rec["event_type"],
            },
            {"$set": rec},
            upsert=True,
        )
    client.close()

if __name__ == "__main__":
    spark = (
        SparkSession.builder.appName("ClickstreamStreaming")
        .getOrCreate()
    )

    # Read from Kafka
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .load()
    )

    # Parse outer JSON, then unwrap nested event fields
    parsed = (
        raw
        .select(from_json(col("value").cast("string"), outer_schema).alias("data"))
        .select("data.event.*")
    )

    # Windowed aggregates per minute by page and event_type
    agg = (
        parsed
        .withColumn("ts", (col("timestamp")).cast("timestamp"))
        .groupBy(
            window(col("ts"), "1 minute").alias("w"),
            col("page"),
            col("event_type"),
        )
        .count()
        .select(
            col("w.start").alias("window_start"),
            col("w.end").alias("window_end"),
            col("page"),
            col("event_type"),
            col("count"),
        )
    )

    # Write to Mongo via foreachBatch
    query = (
        agg.writeStream.outputMode("update")
        .foreachBatch(lambda df, epoch_id: _write_mongo(df, epoch_id))
        .option("checkpointLocation", os.getenv("CHECKPOINT_DIR", "/tmp/checkpoints/clickstream"))
        .start()
    )

    query.awaitTermination()
