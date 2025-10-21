"""
spark_seo_analytics.py - SEO & Traffic Source Analysis
Phân tích nguồn traffic, landing pages, conversion by source
"""

import os
import sys
import traceback

if "JAVA_HOME" not in os.environ:
    os.environ["JAVA_HOME"] = r"C:\LUUDULIEU\APP\JDK\jdk-17.0.12"

os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
python_exe = sys.executable
os.environ["PYSPARK_PYTHON"] = python_exe
os.environ["PYSPARK_DRIVER_PYTHON"] = python_exe

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, sum as spark_sum, when, lit, countDistinct
from db import events_col
from bson import ObjectId


def get_spark():
    """Get or create Spark session"""
    existing = SparkSession._instantiatedSession
    if existing is not None:
        return existing
    
    return SparkSession.builder \
        .appName("SEO-Analytics") \
        .master("local[*]") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.sql.adaptive.enabled", "false") \
        .config("spark.ui.enabled", "false") \
        .config("spark.driver.host", "localhost") \
        .config("spark.driver.bindAddress", "127.0.0.1") \
        .getOrCreate()


def load_events_to_spark(spark, limit=None, username=None):
    """Load events from MongoDB to Spark DataFrame"""
    try:
        pipeline = []
        
        if username:
            user = events_col().database.users.find_one({"username": username})
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
        
        if limit:
            pipeline.append({"$limit": limit})
        
        events = list(events_col().aggregate(pipeline))
        
        if not events:
            return None
        
        spark_data = []
        for e in events:
            props = e.get("properties", {})
            spark_data.append((
                str(e.get("_id")),
                str(e.get("user_id", "")),
                str(e.get("session_id", "")),
                e.get("timestamp"),
                str(e.get("page", "")),
                str(e.get("event_type", "pageview")),
                str(props.get("referrer", "")),
                str(props.get("source", "")),
                str(props.get("category", ""))
            ))
        
        df = spark.createDataFrame(spark_data, [
            "event_id", "user_id", "session_id", "timestamp", "page", 
            "event_type", "referrer", "source", "category"
        ])
        
        return df
        
    except Exception as e:
        print(f"Error loading events: {e}")
        return None


def analyze_traffic_sources(username=None):
    """
    SEO & Traffic Source Analysis
    - Phân tích nguồn traffic (organic, social, direct, paid)
    - Landing page effectiveness
    - Bounce rate by source
    - Conversion rate by source
    """
    try:
        spark = get_spark()
        df = load_events_to_spark(spark, username=username)
        
        if df is None or df.count() == 0:
            return {"error": "No data available"}
        
        df.createOrReplaceTempView("events")
        
        # 1. Traffic by source
        traffic_by_source = spark.sql("""
            SELECT 
                CASE 
                    WHEN referrer LIKE '%google%' OR referrer LIKE '%bing%' THEN 'organic_search'
                    WHEN referrer LIKE '%facebook%' OR referrer LIKE '%twitter%' OR referrer LIKE '%instagram%' THEN 'social'
                    WHEN referrer LIKE '%ads%' OR source = 'ads' THEN 'paid'
                    WHEN referrer = '' OR referrer = 'direct' THEN 'direct'
                    WHEN referrer != '' THEN 'referral'
                    ELSE 'unknown'
                END as traffic_source,
                COUNT(DISTINCT session_id) as sessions,
                COUNT(*) as events,
                COUNT(DISTINCT user_id) as unique_users
            FROM events
            GROUP BY traffic_source
            ORDER BY sessions DESC
        """).collect()
        
        # 2. Landing pages analysis
        landing_pages = spark.sql("""
            SELECT 
                first_page,
                COUNT(*) as sessions,
                AVG(events_per_session) as avg_events,
                SUM(CASE WHEN has_conversion THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as conversion_rate,
                SUM(CASE WHEN is_bounce THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as bounce_rate
            FROM (
                SELECT 
                    session_id,
                    FIRST(page) as first_page,
                    COUNT(*) as events_per_session,
                    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as has_conversion,
                    CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END as is_bounce
                FROM events
                GROUP BY session_id
            )
            GROUP BY first_page
            ORDER BY sessions DESC
            LIMIT 20
        """).collect()
        
        # 3. Conversion rate by source
        conversion_by_source = spark.sql("""
            SELECT 
                traffic_source,
                total_sessions,
                conversion_sessions,
                ROUND(conversion_sessions * 100.0 / total_sessions, 2) as conversion_rate_pct
            FROM (
                SELECT 
                    CASE 
                        WHEN referrer LIKE '%google%' OR referrer LIKE '%bing%' THEN 'organic_search'
                        WHEN referrer LIKE '%facebook%' OR referrer LIKE '%twitter%' THEN 'social'
                        WHEN referrer LIKE '%ads%' OR source = 'ads' THEN 'paid'
                        WHEN referrer = '' OR referrer = 'direct' THEN 'direct'
                        ELSE 'referral'
                    END as traffic_source,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN session_id END) as conversion_sessions
                FROM events
                GROUP BY traffic_source
            )
        """).collect()
        
        # 4. Peak traffic hours
        hourly_traffic = spark.sql("""
            SELECT 
                HOUR(timestamp) as hour,
                CASE 
                    WHEN referrer LIKE '%google%' THEN 'organic'
                    WHEN referrer LIKE '%facebook%' OR referrer LIKE '%twitter%' THEN 'social'
                    WHEN referrer = '' OR referrer = 'direct' THEN 'direct'
                    ELSE 'other'
                END as source,
                COUNT(DISTINCT session_id) as sessions
            FROM events
            GROUP BY hour, source
            ORDER BY hour, sessions DESC
        """).collect()
        
        return {
            "algorithm": "SEO & Traffic Source Analysis",
            "traffic_by_source": [
                {
                    "source": row["traffic_source"],
                    "sessions": int(row["sessions"]),
                    "events": int(row["events"]),
                    "unique_users": int(row["unique_users"])
                }
                for row in traffic_by_source
            ],
            "landing_pages": [
                {
                    "page": row["first_page"],
                    "sessions": int(row["sessions"]),
                    "avg_events": round(float(row["avg_events"]), 2),
                    "conversion_rate": round(float(row["conversion_rate"]), 4),
                    "bounce_rate": round(float(row["bounce_rate"]), 4)
                }
                for row in landing_pages
            ],
            "conversion_by_source": [
                {
                    "source": row["traffic_source"],
                    "total_sessions": int(row["total_sessions"]),
                    "conversion_sessions": int(row["conversion_sessions"]),
                    "conversion_rate_pct": float(row["conversion_rate_pct"])
                }
                for row in conversion_by_source
            ],
            "hourly_traffic": [
                {
                    "hour": int(row["hour"]),
                    "source": row["source"],
                    "sessions": int(row["sessions"])
                }
                for row in hourly_traffic
            ]
        }
        
    except Exception as e:
        print(f"Error in traffic source analysis: {e}")
        traceback.print_exc()
        return {"error": str(e)}
