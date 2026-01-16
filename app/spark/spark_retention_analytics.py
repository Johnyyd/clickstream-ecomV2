"""
Cohort Retention Analytics using Spark
Refactored for reliability - simple MongoDB loads + Spark processing
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime
import os
import logging

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from app.spark.session import get_spark_session
from app.spark.mongo_helpers import load_events_simple
from app.core.db_sync import users_col

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)


def get_spark():
    """Get shared Spark session"""
    return get_spark_session()


def analyze_retention(
    username: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    segment: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    # Default to last 90 days if no date range specified
    if date_from is None and date_to is None:
        from datetime import timedelta

        date_to = datetime.now()
        date_from = date_to - timedelta(days=90)
    """
    Cohort Retention Analysis

    Analyzes:
    - User retention by cohort
    - Return rates
    - Churn rates
    - Cohort performance

    Uses simple MongoDB load + all processing in Spark for reliability.
    """
    try:
        logger.info(
            f"[RETENTION] Start analyze_retention (date_from={date_from}, date_to={date_to})"
        )

        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available"}

        # Load events
        logger.info("[RETENTION] Loading events...")
        events = load_events_simple(
            date_from=date_from, date_to=date_to, exclude_noisy=True
        )

        if not events:
            return {"error": "No data available"}

        logger.info(f"[RETENTION] Loaded {len(events)} events")

        # Load users for cohort info
        logger.info("[RETENTION] Loading users...")
        users = list(users_col().find({}, {"_id": 1, "created_at": 1}))

        # Create DataFrames
        events_data = []
        for e in events:
            events_data.append(
                (
                    str(e.get("user_id", "")),
                    e.get("timestamp"),
                    str(e.get("event_type", "")),
                )
            )

        events_df = spark.createDataFrame(
            events_data, ["user_id", "timestamp", "event_type"]
        )

        users_data = []
        for u in users:
            created = u.get("created_at")
            if isinstance(created, datetime):
                created_ts = int(created.timestamp())
            elif isinstance(created, (int, float)):
                created_ts = int(created)
            else:
                created_ts = 0

            users_data.append((str(u.get("_id")), created_ts))

        users_df = spark.createDataFrame(users_data, ["user_id", "created_at"])

        events_df.cache()
        users_df.cache()

        # Join + create temp views
        df = events_df.join(users_df, "user_id", "left")
        df.createOrReplaceTempView("user_events")

        # Retention analysis
        logger.info("[RETENTION] Computing retention...")
        retention = spark.sql(
            """
            WITH user_activity AS (
                SELECT 
                    user_id,
                    MIN(timestamp) as first_event,
                    MAX(timestamp) as last_event,
                    COUNT(DISTINCT DATE(FROM_UNIXTIME(timestamp))) as active_days,
                    created_at
                FROM user_events
                WHERE created_at > 0
                GROUP BY user_id, created_at
            ),
            cohorts AS (
                SELECT 
                    DATE(FROM_UNIXTIME(created_at)) as cohort_date,
                    user_id,
                    first_event,
                    last_event,
                    active_days,
                    DATEDIFF(DATE(FROM_UNIXTIME(last_event)), DATE(FROM_UNIXTIME(first_event))) as days_retained
                FROM user_activity
            )
            SELECT 
                cohort_date,
                COUNT(DISTINCT user_id) as cohort_size,
                AVG(active_days) as avg_active_days,
                AVG(days_retained) as avg_days_retained,
                COUNT(DISTINCT CASE WHEN days_retained >= 7 THEN user_id END) as retained_7d,
                COUNT(DISTINCT CASE WHEN days_retained >= 30 THEN user_id END) as retained_30d
            FROM cohorts
            GROUP BY cohort_date
            ORDER BY cohort_date DESC
            LIMIT 10
        """
        ).collect()

        # Overall retention rate
        logger.info("[RETENTION] Computing overall retention...")
        overall = spark.sql(
            """
            WITH user_activity AS (
                SELECT 
                    user_id,
                    MIN(timestamp) as first_event,
                    MAX(timestamp) as last_event
                FROM user_events
                GROUP BY user_id
            )
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN DATEDIFF(DATE(FROM_UNIXTIME(last_event)), DATE(FROM_UNIXTIME(first_event))) >= 7 THEN 1 END) as retained_7d,
                COUNT(CASE WHEN DATEDIFF(DATE(FROM_UNIXTIME(last_event)), DATE(FROM_UNIXTIME(first_event))) >= 30 THEN 1 END) as retained_30d
            FROM user_activity
        """
        ).collect()[0]

        events_df.unpersist()
        users_df.unpersist()

        result = {
            "cohorts": [
                {
                    "cohort_date": str(row.cohort_date),
                    "cohort_size": row.cohort_size,
                    "avg_active_days": round(row.avg_active_days, 2),
                    "avg_days_retained": round(row.avg_days_retained, 2),
                    "retained_7d": row.retained_7d,
                    "retained_30d": row.retained_30d,
                    "retention_7d_rate": (
                        round(row.retained_7d * 100.0 / row.cohort_size, 2)
                        if row.cohort_size > 0
                        else 0
                    ),
                    "retention_30d_rate": (
                        round(row.retained_30d * 100.0 / row.cohort_size, 2)
                        if row.cohort_size > 0
                        else 0
                    ),
                }
                for row in retention
            ],
            "overall_retention": {
                "total_users": overall.total_users,
                "retained_7d": overall.retained_7d,
                "retained_30d": overall.retained_30d,
                "retention_7d_rate": (
                    round(overall.retained_7d * 100.0 / overall.total_users, 2)
                    if overall.total_users > 0
                    else 0
                ),
                "retention_30d_rate": (
                    round(overall.retained_30d * 100.0 / overall.total_users, 2)
                    if overall.total_users > 0
                    else 0
                ),
            },
        }

        logger.info("[RETENTION] Analysis complete")
        return result

    except Exception as e:
        logger.error(f"[RETENTION] Error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}
