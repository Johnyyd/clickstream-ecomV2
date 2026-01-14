"""
Customer Journey Analytics using Spark
Refactored for reliability - simple MongoDB loads + Spark processing
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime
import os
import logging

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.spark.session import get_spark_session
from app.spark.mongo_helpers import load_events_simple

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)


def get_spark():
    """Get shared Spark session"""
    return get_spark_session()


def analyze_user_journey(
    username: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    segment: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Customer Journey Analysis

    Analyzes:
    - Common user paths
    - Conversion funnels
    - Drop-off points
    - Path to purchase

    Uses simple MongoDB load + all processing in Spark for reliability.
    """
    try:
        logger.info(
            f"[JOURNEY] Start analyze_user_journey (date_from={date_from}, date_to={date_to})"
        )

        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available"}

        # Simple load
        logger.info("[JOURNEY] Loading events...")
        events = load_events_simple(
            date_from=date_from,
            date_to=date_to,
            event_types=["pageview", "add_to_cart", "purchase"],
            exclude_noisy=True,
        )

        if not events:
            return {"error": "No data available"}

        logger.info(f"[JOURNEY] Loaded {len(events)} events")

        # Create DataFrame
        events_data = []
        for e in events:
            events_data.append(
                (
                    str(e.get("session_id", "")),
                    str(e.get("user_id", "")),
                    e.get("timestamp"),
                    str(e.get("page", "")),
                    str(e.get("event_type", "")),
                )
            )

        df = spark.createDataFrame(
            events_data, ["session_id", "user_id", "timestamp", "page", "event_type"]
        )

        df.cache()
        df.createOrReplaceTempView("events")

        # Common paths
        logger.info("[JOURNEY] Computing common paths...")
        paths = spark.sql(
            """
            WITH ordered_events AS (
                SELECT 
                    session_id,
                    page,
                    event_type,
                    ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY timestamp) as step
                FROM events
                WHERE event_type = 'pageview'
            ),
            session_paths AS (
                SELECT 
                    session_id,
                    CONCAT_WS(' -> ', COLLECT_LIST(page)) as path,
                    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as converted
                FROM ordered_events
                WHERE step <= 5
                GROUP BY session_id
            )
            SELECT 
                path,
                COUNT(*) as frequency,
                SUM(converted) as conversions,
                ROUND(SUM(converted) * 100.0 / COUNT(*), 2) as conversion_rate
            FROM session_paths
            GROUP BY path
            ORDER BY frequency DESC
            LIMIT 20
        """
        ).collect()

        # Funnel analysis
        logger.info("[JOURNEY] Computing funnel...")
        funnel = spark.sql(
            """
            SELECT 
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(DISTINCT CASE WHEN event_type = 'pageview' THEN session_id END) as viewed,
                COUNT(DISTINCT CASE WHEN event_type = 'add_to_cart' THEN session_id END) as added_to_cart,
                COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN session_id END) as purchased
            FROM events
        """
        ).collect()[0]

        df.unpersist()

        result = {
            "common_paths": [
                {
                    "path": row.path,
                    "frequency": row.frequency,
                    "conversions": row.conversions,
                    "conversion_rate": row.conversion_rate,
                }
                for row in paths
            ],
            "funnel": {
                "total_sessions": funnel.total_sessions,
                "viewed": funnel.viewed,
                "added_to_cart": funnel.added_to_cart,
                "purchased": funnel.purchased,
                "view_to_cart_rate": (
                    round(funnel.added_to_cart * 100.0 / funnel.viewed, 2)
                    if funnel.viewed > 0
                    else 0
                ),
                "cart_to_purchase_rate": (
                    round(funnel.purchased * 100.0 / funnel.added_to_cart, 2)
                    if funnel.added_to_cart > 0
                    else 0
                ),
            },
        }

        logger.info("[JOURNEY] Analysis complete")
        return result

    except Exception as e:
        logger.error(f"[JOURNEY] Error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}
