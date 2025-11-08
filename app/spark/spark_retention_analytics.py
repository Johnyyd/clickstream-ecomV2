"""
spark_retention_analytics.py - Cohort & Retention Analysis
Phân tích retention theo cohort, churn rate
"""

import os
import logging
import traceback
from datetime import datetime

from pyspark.sql.functions import col, count, countDistinct, datediff, first, last, to_date
from bson import ObjectId

from app.core.spark import spark_manager
from app.core.db_sync import users_col, events_col

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)


def get_spark():
    """Get shared Spark session"""
    return spark_manager.get_session()


def load_events_to_spark(spark, username=None):
    """Load events from MongoDB with referrer/source normalization for robust analytics
    - Adds normalized referrer (properties.referrer -> utm_source -> properties.source)
    - Keeps original source for additional heuristics. Extra columns are ignored by existing queries.
    """
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
            props = e.get("properties", {}) or {}
            ref = (props.get("referrer") or props.get("utm_source") or "")
            if isinstance(ref, str):
                ref = ref.strip().lower()
            else:
                ref = str(ref)
            src = props.get("source") or ""
            if isinstance(src, str):
                src = src.strip().lower()
            else:
                src = str(src)
            spark_data.append((
                str(e.get("user_id", "")),
                str(e.get("session_id", "")),
                e.get("timestamp"),
                str(e.get("event_type", "pageview")),
                ref,
                src,
            ))
        
        df = spark.createDataFrame(spark_data, ["user_id", "session_id", "timestamp", "event_type", "referrer", "source"])
        return df
        
    except Exception as e:
        print(f"Error loading events: {e}")
        return None


def analyze_cohort_retention(username=None):
    """
    Cohort & Retention Analysis
    - User cohorts by signup date
    - Retention rate over time
    - User segments by activity
    """
    try:
        logger.info("[Retention] Start analyze_cohort_retention (username=%s)", username)
        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available. Install Java 8/11 and set JAVA_HOME."}
        
        # Load user data
        query = {}
        if username:
            user = users_col().find_one({"username": username})
            if user:
                query["_id"] = user["_id"]
        
        users = list(users_col().find(query, {"_id": 1, "created_at": 1}))
        logger.info("[Retention] Loaded %d users", len(users))
        
        if not users:
            return {"error": "No user data available"}
        
        # Load events
        df_events = load_events_to_spark(spark, username=username)
        if df_events is None:
            return {"error": "No event data available"}
        logger.info("[Retention] Events DF count=%d", df_events.count())
        
        df_events.createOrReplaceTempView("events")
        # Enrich with consistent traffic_source for optional source KPIs
        spark.sql("""
            CREATE OR REPLACE TEMP VIEW events_enriched AS
            SELECT 
                *,
                CASE 
                    WHEN referrer LIKE '%google%' OR referrer LIKE '%bing%' THEN 'organic_search'
                    WHEN referrer LIKE '%facebook%' OR referrer LIKE '%twitter%' OR referrer LIKE '%instagram%' THEN 'social'
                    WHEN referrer LIKE '%ads%' OR source = 'ads' THEN 'paid'
                    WHEN referrer = '' OR referrer = 'direct' THEN 'direct'
                    WHEN referrer != '' THEN 'referral'
                    ELSE 'unknown'
                END AS traffic_source
            FROM events
        """)
        
        # Create user cohorts
        user_data = []
        for user in users:
            user_id = str(user["_id"])
            created_at = user.get("created_at")
            if not created_at:
                continue
            
            cohort_date = created_at.strftime("%Y-%m-%d") if isinstance(created_at, datetime) else str(created_at)[:10]
            
            user_data.append((
                user_id,
                cohort_date,
                created_at
            ))
        
        if not user_data:
            return {"error": "No valid user data with signup dates"}
        
        df_users = spark.createDataFrame(user_data, ["user_id", "cohort_date", "signup_timestamp"])
        df_users.createOrReplaceTempView("users")
        
        # Calculate retention
        logger.info("[Retention] Computing cohort retention ...")
        retention_data = spark.sql("""
            SELECT 
                u.cohort_date,
                COUNT(DISTINCT u.user_id) as cohort_size,
                COUNT(DISTINCT CASE 
                    WHEN DATEDIFF(DATE(to_timestamp(from_unixtime(e.timestamp))), DATE(u.signup_timestamp)) BETWEEN 1 AND 7 
                    THEN e.user_id 
                END) as retained_week1,
                COUNT(DISTINCT CASE 
                    WHEN DATEDIFF(DATE(to_timestamp(from_unixtime(e.timestamp))), DATE(u.signup_timestamp)) BETWEEN 8 AND 14 
                    THEN e.user_id 
                END) as retained_week2,
                COUNT(DISTINCT CASE 
                    WHEN DATEDIFF(DATE(to_timestamp(from_unixtime(e.timestamp))), DATE(u.signup_timestamp)) BETWEEN 15 AND 30 
                    THEN e.user_id 
                END) as retained_month1
            FROM users u
            LEFT JOIN events e ON u.user_id = e.user_id
            GROUP BY u.cohort_date
            ORDER BY u.cohort_date DESC
            LIMIT 10
        """).collect()
        
        cohorts = []
        for row in retention_data:
            cohort_size = int(row["cohort_size"])
            if cohort_size > 0:
                cohorts.append({
                    "cohort_date": row["cohort_date"],
                    "cohort_size": cohort_size,
                    "retention_week1": round(int(row["retained_week1"]) / cohort_size * 100, 2),
                    "retention_week2": round(int(row["retained_week2"]) / cohort_size * 100, 2),
                    "retention_month1": round(int(row["retained_month1"]) / cohort_size * 100, 2)
                })
        
        # Calculate average retention
        avg_retention = {
            "week1": round(sum(c["retention_week1"] for c in cohorts) / len(cohorts), 2) if cohorts else 0,
            "week2": round(sum(c["retention_week2"] for c in cohorts) / len(cohorts), 2) if cohorts else 0,
            "month1": round(sum(c["retention_month1"] for c in cohorts) / len(cohorts), 2) if cohorts else 0
        }
        
        # User activity segments
        logger.info("[Retention] Computing user activity segments ...")
        user_segments = spark.sql("""
            SELECT 
                CASE 
                    WHEN days_since_last_activity <= 7 THEN 'Active'
                    WHEN days_since_last_activity <= 30 THEN 'At Risk'
                    ELSE 'Churned'
                END as segment,
                COUNT(*) as user_count
            FROM (
                SELECT 
                    user_id,
                    DATEDIFF(CURRENT_DATE(), MAX(DATE(timestamp))) as days_since_last_activity
                FROM events
                GROUP BY user_id
            )
            GROUP BY segment
        """).collect()

        # Optional: Engagement by traffic source
        logger.info("[Retention] Computing engagement by source (optional) ...")
        engagement_by_source = spark.sql("""
            SELECT 
                traffic_source,
                COUNT(*) as events,
                COUNT(DISTINCT session_id) as sessions,
                COUNT(DISTINCT user_id) as unique_users
            FROM events_enriched
            GROUP BY traffic_source
            ORDER BY sessions DESC
        """).collect()
        
        logger.info("[Retention] Done. Cohorts=%d", len(cohorts))
        return {
            "algorithm": "Cohort & Retention Analysis",
            "cohorts": cohorts,
            "average_retention": avg_retention,
            "user_segments": [
                {
                    "segment": row["segment"],
                    "user_count": int(row["user_count"])
                }
                for row in user_segments
            ],
            "engagement_by_source": [
                {
                    "source": row["traffic_source"],
                    "events": int(row["events"]),
                    "sessions": int(row["sessions"]),
                    "unique_users": int(row["unique_users"]),
                }
                for row in engagement_by_source
            ]
        }
        
    except Exception as e:
        logger.exception("[Retention] Error: %s", e)
        traceback.print_exc()
        return {"error": str(e)}


def save_retention_summary(username: str | None = None) -> dict:
    """Compute and persist retention summary to Mongo for fast retrieval."""
    logger.info("[Retention] Saving retention summary (username=%s)", username)
    res = analyze_cohort_retention(username=username)
    if "error" in res:
        return res
    try:
        db = events_col().database
        col_out = db["analytics_retention"]
        doc = {
            "username": username,
            "generated_at": datetime.utcnow(),
            "summary": res,
        }
        col_out.insert_one(doc)
        logger.info("[Retention] Summary saved to analytics_retention id=%s", str(doc.get("_id")))
        return {"status": "ok", "collection": "analytics_retention", "id": str(doc.get("_id"))}
    except Exception as e:
        return {"error": str(e)}
