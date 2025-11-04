"""
spark_journey_analytics.py - Customer Journey Path Analysis
Phân tích đường đi của khách hàng, drop-off points, conversion paths
"""

import os
import logging
import traceback
from datetime import datetime

from pyspark.sql.functions import col, count, first, last, avg, sum as spark_sum, lit, collect_list, struct
from pyspark.sql.window import Window
from bson import ObjectId

from app.core.spark import spark_manager
from app.core.db_sync import events_col, users_col

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)

def get_spark():
    """Get shared Spark session"""
    return spark_manager.get_session()


def load_events_to_spark(spark, username=None):
    """Load events from MongoDB"""
    try:
        pipeline = []
        if username:
            user = users_col().find_one({"username": username})
            if user:
                pipeline.append({"$match": {"user_id": user["_id"]}})
        
        pipeline.append({
            "$match": {
                "flag.noisy": {"$ne": True},
                "$or": [
                    {"properties.source": {"$exists": False}},
                    {"properties.source": {"$nin": ["simulation", "basic_sim", "seed_demo"]}}
                ]
            }
        })
        
        events = list(events_col().aggregate(pipeline))
        
        if not events:
            return None
        
        spark_data = []
        for e in events:
            spark_data.append((
                str(e.get("session_id", "")),
                e.get("timestamp"),
                str(e.get("page", "")),
                str(e.get("event_type", "pageview"))
            ))
        
        df = spark.createDataFrame(spark_data, ["session_id", "timestamp", "page", "event_type"])
        return df
        
    except Exception as e:
        print(f"Error loading events: {e}")
        return None


def analyze_customer_journey(username=None):
    """
    Customer Journey Path Analysis
    - Most common paths to conversion
    - Drop-off points
    - Path length analysis
    - Common page sequences
    """
    try:
        logger.info("[Journey] Start analyze_customer_journey (username=%s)", username)
        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available. Install Java 8/11 and set JAVA_HOME."}
        
        df = load_events_to_spark(spark, username=username)
        
        if df is None or df.count() == 0:
            return {"error": "No data available"}
        logger.info("[Journey] Events DF count=%d", df.count())
        
        df.createOrReplaceTempView("events")
        
        # 1. Identify conversion paths (sessions that led to purchase)
        logger.info("[Journey] Computing conversion paths ...")
        conversion_paths = spark.sql("""
            SELECT 
                session_id,
                CONCAT_WS(' -> ', COLLECT_LIST(page_simplified)) as path,
                COUNT(*) as path_length,
                MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as converted
            FROM (
                SELECT 
                    session_id,
                    timestamp,
                    event_type,
                    CASE 
                        WHEN page LIKE '/p/%' OR page LIKE '/product%' THEN 'product'
                        WHEN page LIKE '/category%' THEN 'category'
                        WHEN page LIKE '/search%' THEN 'search'
                        WHEN page LIKE '/cart%' THEN 'cart'
                        WHEN page LIKE '/checkout%' THEN 'checkout'
                        ELSE page
                    END as page_simplified
                FROM events
                ORDER BY session_id, timestamp
            )
            GROUP BY session_id
            HAVING converted = 1
            ORDER BY path_length
            LIMIT 50
        """).collect()
        
        # 2. Common drop-off points
        logger.info("[Journey] Computing drop-off points ...")
        dropoff_analysis = spark.sql("""
            SELECT 
                last_page,
                COUNT(*) as dropout_count,
                AVG(events_before_dropout) as avg_events_before
            FROM (
                SELECT 
                    session_id,
                    LAST(page_simplified) as last_page,
                    COUNT(*) as events_before_dropout,
                    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as converted
                FROM (
                    SELECT 
                        session_id,
                        event_type,
                        CASE 
                            WHEN page LIKE '/p/%' OR page LIKE '/product%' THEN 'product'
                            WHEN page LIKE '/category%' THEN 'category'
                            WHEN page LIKE '/cart%' THEN 'cart'
                            WHEN page LIKE '/checkout%' THEN 'checkout'
                            ELSE page
                        END as page_simplified
                    FROM events
                )
                GROUP BY session_id
                HAVING converted = 0
            )
            GROUP BY last_page
            ORDER BY dropout_count DESC
            LIMIT 10
        """).collect()
        
        # 3. Average path length to conversion
        logger.info("[Journey] Computing path statistics ...")
        path_stats = spark.sql("""
            SELECT 
                AVG(path_length) as avg_path_length,
                MIN(path_length) as min_path_length,
                MAX(path_length) as max_path_length,
                PERCENTILE(path_length, 0.5) as median_path_length
            FROM (
                SELECT 
                    session_id,
                    COUNT(*) as path_length
                FROM events
                WHERE session_id IN (
                    SELECT DISTINCT session_id 
                    FROM events 
                    WHERE event_type = 'purchase'
                )
                GROUP BY session_id
            )
        """).collect()[0]
        
        # 4. Most common page sequences (n-grams)
        logger.info("[Journey] Computing common page sequences ...")
        page_sequences = spark.sql("""
            SELECT 
                CONCAT(page1, ' -> ', page2) as sequence,
                COUNT(*) as frequency
            FROM (
                SELECT 
                    session_id,
                    page_simplified as page1,
                    LEAD(page_simplified) OVER (PARTITION BY session_id ORDER BY timestamp) as page2
                FROM (
                    SELECT 
                        session_id,
                        timestamp,
                        CASE 
                            WHEN page LIKE '/p/%' THEN 'product'
                            WHEN page LIKE '/category%' THEN 'category'
                            WHEN page LIKE '/cart%' THEN 'cart'
                            WHEN page LIKE '/checkout%' THEN 'checkout'
                            ELSE page
                        END as page_simplified
                    FROM events
                )
            )
            WHERE page2 IS NOT NULL
            GROUP BY page1, page2
            ORDER BY frequency DESC
            LIMIT 20
        """).collect()
        
        logger.info("[Journey] Done. conv_paths=%d, dropoffs=%d", len(conversion_paths), len(dropoff_analysis))
        return {
            "algorithm": "Customer Journey Path Analysis",
            "conversion_paths": [
                {
                    "session_id": row["session_id"][:16] + "...",
                    "path": row["path"],
                    "path_length": int(row["path_length"])
                }
                for row in conversion_paths[:20]
            ],
            "dropoff_points": [
                {
                    "page": row["last_page"],
                    "dropout_count": int(row["dropout_count"]),
                    "avg_events_before": round(float(row["avg_events_before"]), 2)
                }
                for row in dropoff_analysis
            ],
            "path_statistics": {
                "avg_path_length": round(float(path_stats["avg_path_length"]), 2),
                "min_path_length": int(path_stats["min_path_length"]),
                "max_path_length": int(path_stats["max_path_length"]),
                "median_path_length": round(float(path_stats["median_path_length"]), 2)
            },
            "common_sequences": [
                {
                    "sequence": row["sequence"],
                    "frequency": int(row["frequency"])
                }
                for row in page_sequences
            ]
        }
        
    except Exception as e:
        logger.exception("[Journey] Error: %s", e)
        traceback.print_exc()
        return {"error": str(e)}


def save_journey_summary(username: str | None = None) -> dict:
    """Compute and persist journey summary to Mongo for fast retrieval."""
    logger.info("[Journey] Saving journey summary (username=%s)", username)
    res = analyze_customer_journey(username=username)
    if "error" in res:
        return res
    try:
        db = events_col().database
        col_out = db["analytics_journey"]
        doc = {
            "username": username,
            "generated_at": datetime.utcnow(),
            "summary": res,
        }
        col_out.insert_one(doc)
        logger.info("[Journey] Summary saved to analytics_journey id=%s", str(doc.get("_id")))
        return {"status": "ok", "collection": "analytics_journey", "id": str(doc.get("_id"))}
    except Exception as e:
        return {"error": str(e)}
