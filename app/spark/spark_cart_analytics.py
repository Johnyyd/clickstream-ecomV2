"""
Cart Abandonment Analytics using Spark
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
from app.core.db_sync import events_col, carts_col
from app.spark.mongo_helpers import load_events_simple

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)


def get_spark():
    """Get shared Spark session"""
    return get_spark_session()


def analyze_cart_abandonment(
    username: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    segment: Optional[str] = None,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cart Abandonment Analysis

    Analyzes:
    - Cart abandonment rate
    - Products most abandoned
    - Time to abandonment
    - Recovery opportunities

    Uses simple MongoDB load + all processing in Spark for reliability.
    """
    try:
        logger.info(
            f"[CART] Start analyze_cart_abandonment (date_from={date_from}, date_to={date_to})"
        )

        spark = get_spark()
        if spark is None:
            return {
                "error": "Spark not available. Install Java 8/11 and set JAVA_HOME."
            }

        # Step 1: Load events (add_to_cart, purchase, etc.)
        logger.info("[CART] Loading events...")
        events = load_events_simple(
            date_from=date_from,
            date_to=date_to,
            event_types=["add_to_cart", "remove_from_cart", "purchase", "view_cart"],
            exclude_noisy=True,
        )

        if not events:
            logger.warning("[CART] No cart events found")
            return {"error": "No data available"}

        logger.info(f"[CART] Loaded {len(events)} cart-related events")

        # Step 2: Load cart data separately (simple query)
        logger.info("[CART] Loading cart data...")
        cart_query = {}
        if date_from:
            cart_query["created_at"] = {"$gte": date_from}
        if date_to:
            if "created_at" not in cart_query:
                cart_query["created_at"] = {}
            cart_query["created_at"]["$lte"] = date_to

        carts = list(carts_col().find(cart_query))
        logger.info(f"[CART] Loaded {len(carts)} carts")

        # Step 3: Create Spark DataFrames
        # Events DataFrame
        events_data = []
        for e in events:
            props = e.get("properties", {}) or {}
            events_data.append(
                (
                    str(e.get("_id")),
                    str(e.get("user_id", "")),
                    str(e.get("session_id", "")),
                    e.get("timestamp"),
                    str(e.get("event_type", "")),
                    str(props.get("product_id", "")),
                    str(props.get("product_name", "")),
                    float(props.get("price", 0)),
                    int(props.get("quantity", 1)),
                )
            )

        events_df = spark.createDataFrame(
            events_data,
            [
                "event_id",
                "user_id",
                "session_id",
                "timestamp",
                "event_type",
                "product_id",
                "product_name",
                "price",
                "quantity",
            ],
        )

        # Carts DataFrame
        carts_data = []
        for c in carts:
            items = c.get("items", [])
            for item in items:
                carts_data.append(
                    (
                        str(c.get("_id")),
                        str(c.get("user_id", "")),
                        str(c.get("session_id", "")),
                        (
                            int(c.get("created_at", 0))
                            if isinstance(c.get("created_at"), (int, float))
                            else (
                                int(c.get("created_at").timestamp())
                                if c.get("created_at")
                                else 0
                            )
                        ),
                        (
                            int(c.get("updated_at", 0))
                            if isinstance(c.get("updated_at"), (int, float))
                            else (
                                int(c.get("updated_at").timestamp())
                                if c.get("updated_at")
                                else 0
                            )
                        ),
                        str(c.get("status", "")),
                        str(item.get("product_id", "")),
                        int(item.get("quantity", 1)),
                        float(item.get("price", 0)),
                    )
                )

        carts_df = spark.createDataFrame(
            carts_data,
            [
                "cart_id",
                "user_id",
                "session_id",
                "created_at",
                "updated_at",
                "status",
                "product_id",
                "quantity",
                "price",
            ],
        )

        # Cache for reuse
        events_df.cache()
        carts_df.cache()

        logger.info(
            f"[CART] Created DataFrames: events={events_df.count()}, carts={carts_df.count()}"
        )

        # Step 4: Analytics in Spark SQL
        events_df.createOrReplaceTempView("cart_events")
        carts_df.createOrReplaceTempView("carts")

        # 1. Abandonment rate by session
        logger.info("[CART] Computing abandonment rate...")
        abandonment = spark.sql(
            """
            WITH session_cart_activity AS (
                SELECT 
                    session_id,
                    user_id,
                    COUNT(CASE WHEN event_type = 'add_to_cart' THEN 1 END) as adds,
                    COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as purchases,
                    MAX(timestamp) as last_activity
                FROM cart_events
                GROUP BY session_id, user_id
            )
            SELECT 
                COUNT(*) as total_sessions,
                SUM(CASE WHEN adds > 0 AND purchases = 0 THEN 1 ELSE 0 END) as abandoned_sessions,
                ROUND(SUM(CASE WHEN adds > 0 AND purchases = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abandonment_rate
            FROM session_cart_activity
            WHERE adds > 0
        """
        ).collect()[0]

        # 2. Most abandoned products
        logger.info("[CART] Computing most abandoned products...")
        abandoned_products = spark.sql(
            """
            SELECT 
                c.product_id,
                MAX(e.product_name) as product_name,
                COUNT(DISTINCT c.cart_id) as times_abandoned,
                SUM(c.quantity) as total_quantity_abandoned,
                ROUND(AVG(c.price), 2) as avg_price
            FROM carts c
            LEFT JOIN cart_events e ON c.product_id = e.product_id
            WHERE c.status = 'abandoned' OR c.status = 'active'
            GROUP BY c.product_id
            ORDER BY times_abandoned DESC
            LIMIT 20
        """
        ).collect()

        # 3. Time to abandonment
        logger.info("[CART] Computing time to abandonment...")
        time_to_abandon = spark.sql(
            """
            SELECT 
                ROUND(AVG(updated_at - created_at) / 60, 2) as avg_minutes_to_abandon,
                ROUND(MIN(updated_at - created_at) / 60, 2) as min_minutes,
                ROUND(MAX(updated_at - created_at) / 60, 2) as max_minutes
            FROM carts
            WHERE status IN ('abandoned', 'active')
            AND updated_at > created_at
        """
        ).collect()

        # 4. Cart value distribution
        logger.info("[CART] Computing cart value...")
        cart_value = spark.sql(
            """
            SELECT 
                ROUND(SUM(quantity * price), 2) as total_abandoned_value,
                ROUND(AVG(quantity * price), 2) as avg_item_value,
                COUNT(DISTINCT cart_id) as abandoned_carts
            FROM carts
            WHERE status IN ('abandoned', 'active')
        """
        ).collect()[0]

        # Cleanup
        events_df.unpersist()
        carts_df.unpersist()

        # Format results
        result = {
            "abandonment_stats": {
                "total_sessions": abandonment.total_sessions,
                "abandoned_sessions": abandonment.abandoned_sessions,
                "abandonment_rate": abandonment.abandonment_rate,
                "total_abandoned_value": cart_value.total_abandoned_value or 0,
                "avg_item_value": cart_value.avg_item_value or 0,
                "abandoned_carts": cart_value.abandoned_carts,
            },
            "most_abandoned_products": [
                {
                    "product_id": row.product_id,
                    "product_name": row.product_name or "Unknown",
                    "times_abandoned": row.times_abandoned,
                    "total_quantity": row.total_quantity_abandoned,
                    "avg_price": row.avg_price,
                }
                for row in abandoned_products
            ],
            "time_to_abandonment": (
                {
                    "avg_minutes": (
                        time_to_abandon[0].avg_minutes_to_abandon
                        if time_to_abandon
                        else 0
                    ),
                    "min_minutes": (
                        time_to_abandon[0].min_minutes if time_to_abandon else 0
                    ),
                    "max_minutes": (
                        time_to_abandon[0].max_minutes if time_to_abandon else 0
                    ),
                }
                if time_to_abandon
                else {}
            ),
        }

        logger.info("[CART] Analysis complete")
        return result

    except Exception as e:
        logger.error(f"[CART] Error: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}
