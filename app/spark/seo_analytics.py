"""
SEO & Traffic Source Analytics using Spark
Refactored for reliability - simple MongoDB loads + Spark processing
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime
import os
import logging

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.spark.session import get_spark_session
from app.core.db_sync import events_col
from app.spark.mongo_helpers import load_events_simple

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)


def get_spark():
    """Get shared Spark session"""
    return get_spark_session()


def analyze_traffic_sources(
    username: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    segment: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """
    SEO & Traffic Source Analysis

    Analyzes:
    - Traffic by source (organic, social, direct, paid, referral)
    - Landing page effectiveness
    - Bounce rate by source
    - Conversion rate by source

    Uses simple MongoDB load + all processing in Spark for reliability.
    """
    try:
        logger.info(
            f"[SEO] Start analyze_traffic_sources (username={username}, date_from={date_from}, date_to={date_to})"
        )

        spark = get_spark()
        if spark is None:
            return {
                "error": "Spark not available. Install Java 8/11 and set JAVA_HOME."
            }

        # Step 1: Simple load from MongoDB (fast and reliable!)
        logger.info("[SEO] Loading events...")
        events = load_events_simple(
            date_from=date_from, date_to=date_to, exclude_noisy=True
        )

        if not events:
            logger.warning("[SEO] No events found")
            return {"error": "No data available"}

        logger.info(f"[SEO] Loaded {len(events)} events")

        # Step 2: Create Spark DataFrame
        # Extract and normalize fields for Spark
        spark_data = []
        for e in events:
            props = e.get("properties", {}) or {}

            # Normalize referrer/source
            referrer = props.get("referrer") or props.get("utm_source") or ""
            if isinstance(referrer, str):
                referrer = referrer.strip().lower()
            else:
                referrer = str(referrer)

            # Categorize source
            source = "direct"
            if referrer:
                if "google" in referrer or "bing" in refer or "search" in referrer:
                    source = "organic"
                elif (
                    "facebook" in referrer
                    or "twitter" in referrer
                    or "linkedin" in referrer
                ):
                    source = "social"
                elif "ads" in referrer or "adwords" in referrer:
                    source = "paid"
                else:
                    source = "referral"

            # Check if ads-related in original source
            orig_source = props.get("source", "")
            if "ads" in str(orig_source).lower():
                source = "paid"

            spark_data.append(
                (
                    str(e.get("_id")),
                    str(e.get("user_id", "")),
                    str(e.get("session_id", "")),
                    e.get("timestamp"),
                    str(e.get("page", "")),
                    str(e.get("event_type", "pageview")),
                    referrer,
                    source,
                    str(props.get("category", "")),
                )
            )

        df = spark.createDataFrame(
            spark_data,
            [
                "event_id",
                "user_id",
                "session_id",
                "timestamp",
                "page",
                "event_type",
                "referrer",
                "source",
                "category",
            ],
        )

        # Cache for reuse
        df.cache()

        logger.info(f"[SEO] Created DataFrame with {df.count()} events")

        # Step 3: Analytics in Spark SQL
        df.createOrReplaceTempView("events")

        # 1. Traffic by source
        logger.info("[SEO] Computing traffic by source...")
        traffic_by_source = spark.sql(
            """
            SELECT 
                source,
                COUNT(*) as visits,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT session_id) as sessions
            FROM events
            GROUP BY source
            ORDER BY visits DESC
        """
        ).collect()

        # 2. Landing pages (first page view per session)
        logger.info("[SEO] Computing landing pages...")
        landing_pages = spark.sql(
            """
            SELECT 
                page as landing_page,
                source,
                COUNT(DISTINCT session_id) as sessions,
                COUNT(DISTINCT user_id) as unique_users
            FROM (
                SELECT 
                    session_id,
                    user_id,
                    page,
                    source,
                    ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY timestamp) as rn
                FROM events
                WHERE event_type = 'pageview'
            )
            WHERE rn = 1
            GROUP BY page, source
            ORDER BY sessions DESC
            LIMIT 20
        """
        ).collect()

        # 3. Bounce rate by source (single-page sessions)
        logger.info("[SEO] Computing bounce rate...")
        bounce_rate = spark.sql(
            """
            WITH session_pages AS (
                SELECT 
                    session_id,
                    source,
                    COUNT(DISTINCT page) as page_count
                FROM events
                WHERE event_type = 'pageview'
                GROUP BY session_id, source
            )
            SELECT 
                source,
                COUNT(*) as total_sessions,
                SUM(CASE WHEN page_count = 1 THEN 1 ELSE 0 END) as bounced_sessions,
                ROUND(SUM(CASE WHEN page_count = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as bounce_rate
            FROM session_pages
            GROUP BY source
            ORDER BY total_sessions DESC
        """
        ).collect()

        # 4. Conversion rate by source
        logger.info("[SEO] Computing conversion rate...")
        conversion_rate = spark.sql(
            """
            SELECT 
                source,
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN session_id END) as converted_sessions,
                ROUND(COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN session_id END) * 100.0 / 
                      COUNT(DISTINCT session_id), 2) as conversion_rate
            FROM events
            GROUP BY source
            ORDER BY total_sessions DESC
        """
        ).collect()

        # Cleanup
        df.unpersist()

        # Format results
        result = {
            "traffic_by_source": [
                {
                    "source": row.source,
                    "visits": row.visits,
                    "unique_users": row.unique_users,
                    "sessions": row.sessions,
                }
                for row in traffic_by_source
            ],
            "landing_pages": [
                {
                    "landing_page": row.landing_page,
                    "source": row.source,
                    "sessions": row.sessions,
                    "unique_users": row.unique_users,
                }
                for row in landing_pages
            ],
            "bounce_rate_by_source": [
                {
                    "source": row.source,
                    "total_sessions": row.total_sessions,
                    "bounced_sessions": row.bounced_sessions,
                    "bounce_rate": row.bounce_rate,
                }
                for row in bounce_rate
            ],
            "conversion_by_source": [
                {
                    "source": row.source,
                    "total_sessions": row.total_sessions,
                    "converted_sessions": row.converted_sessions,
                    "conversion_rate": row.conversion_rate,
                }
                for row in conversion_rate
            ],
        }

        logger.info("[SEO] Analysis complete")
        return result

    except Exception as e:
        logger.error(f"[SEO] Error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}
