"""
Spark journey analytics optimized implementation
"""
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from datetime import datetime

from app.core.spark import create_spark_session, optimize_spark_df
from app.core.db_sync import events_col

def analyze_user_journeys(events_df, min_path_freq=10):
    """
    Analyze user journey patterns with optimized implementation
    
    Args:
        events_df: Spark DataFrame with events
        min_path_freq: Minimum frequency for path to be included
    """
    # Optimize input DataFrame
    events_df = optimize_spark_df(events_df)
    
    # Create session path strings
    w = Window.partitionBy("session_id").orderBy("timestamp")
    paths_df = (events_df
        .select(
            "session_id",
            "event_type",
            "timestamp",
            F.lag("event_type").over(w).alias("prev_event")
        )
        .withColumn(
            "path",
            F.concat_ws("->", F.collect_list("event_type").over(w))
        )
        .groupBy("session_id")
        .agg(
            F.last("path").alias("full_path"),
            F.count("*").alias("path_length")
        )
    )
    
    # Analyze common paths
    common_paths = (paths_df
        .groupBy("full_path")
        .agg(F.count("*").alias("frequency"))
        .where(F.col("frequency") >= min_path_freq)
        .orderBy(F.desc("frequency"))
        .cache()
    )
    
    # Calculate conversion metrics
    total_sessions = paths_df.count()
    converted = paths_df.filter(F.col("full_path").like("%checkout%")).count()
    conversion_rate = converted / total_sessions if total_sessions > 0 else 0
    
    # Calculate path metrics
    path_metrics = (paths_df
        .agg(
            F.avg("path_length").alias("avg_path_length"),
            F.percentile_approx("path_length", 0.5).alias("median_path_length"),
            F.max("path_length").alias("max_path_length")
        )
        .collect()[0]
    )
    
    return {
        "common_paths": [
            {"path": row["full_path"], "frequency": row["frequency"]}
            for row in common_paths.collect()
        ],
        "path_metrics": {
            "average_length": path_metrics["avg_path_length"],
            "median_length": path_metrics["median_path_length"],
            "max_length": path_metrics["max_path_length"]
        },
        "conversion_rate": conversion_rate
    }

def analyze_customer_journeys(username: str | None = None, limit: int | None = None):
    """Backward-compatible wrapper expected by orchestrator.
    Loads events from MongoDB, constructs a Spark DataFrame, and delegates to analyze_user_journeys.
    """
    try:
        spark = create_spark_session("journey-analytics")
        # Build Mongo query
        query = {}
        if username:
            try:
                user = events_col().database.users.find_one({"username": username})
                if user:
                    query["user_id"] = user.get("_id")
            except Exception:
                pass

        cur = events_col().find(query, projection={"session_id": 1, "event_type": 1, "timestamp": 1}).sort("timestamp", 1)
        if limit:
            try:
                cur = cur.limit(int(limit))
            except Exception:
                pass
        docs = list(cur)
        if not docs:
            return {
                "common_paths": [],
                "path_metrics": {"average_length": 0, "median_length": 0, "max_length": 0},
                "conversion_rate": 0.0,
            }

        rows = []
        for d in docs:
            ts = d.get("timestamp")
            if isinstance(ts, (int, float)):
                ts = datetime.utcfromtimestamp(ts)
            rows.append((
                d.get("session_id", ""),
                d.get("event_type", ""),
                ts
            ))

        df = spark.createDataFrame(rows, ["session_id", "event_type", "timestamp"])
        return analyze_user_journeys(df)
    except Exception as e:
        return {"error": str(e)}