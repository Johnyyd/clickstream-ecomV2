"""
Spark cart analytics optimized implementation
"""
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from app.core.spark import create_spark_session, optimize_spark_df

def analyze_cart_behavior(events_df, lookback_days=30):
    """
    Analyze shopping cart behavior with optimized implementation
    
    Args:
        events_df: Spark DataFrame with events
        lookback_days: Days to analyze
    """
    # Filter relevant events and optimize
    cart_events = optimize_spark_df(
        events_df.filter(
            F.col("event_type").isin(["add_to_cart", "remove_from_cart", "checkout", "purchase"])
        )
    )
    
    # Create cart sessions
    w = Window.partitionBy("session_id").orderBy("timestamp")
    cart_sessions = (cart_events
        .withColumn(
            "cart_action",
            F.when(F.col("event_type") == "add_to_cart", 1)
             .when(F.col("event_type") == "remove_from_cart", -1)
             .otherwise(0)
        )
        .withColumn(
            "cart_items",
            F.sum("cart_action").over(w)
        )
        .groupBy("session_id")
        .agg(
            F.max("cart_items").alias("max_items"),
            F.last("event_type").alias("last_event"),
            F.collect_set("properties.product_id").alias("products")
        )
        .cache()
    )
    
    # Calculate metrics
    total_carts = cart_sessions.count()
    completed = cart_sessions.filter(F.col("last_event") == "purchase").count()
    
    # Analyze item combinations
    product_combinations = (cart_sessions
        .where(F.size("products") > 1)
        .select(F.explode(F.arrays_zip("products")).alias("product_combo"))
        .groupBy("product_combo")
        .agg(F.count("*").alias("frequency"))
        .orderBy(F.desc("frequency"))
        .limit(10)
    )
    
    # Calculate recovery opportunities
    abandoned_carts = (cart_sessions
        .filter(
            (F.col("last_event") != "purchase") &
            (F.col("max_items") > 0)
        )
        .select("session_id", "products")
    )
    
    return {
        "cart_metrics": {
            "abandonment_rate": 1 - (completed / total_carts) if total_carts > 0 else 0,
            "avg_items": cart_sessions.select(F.avg("max_items")).collect()[0][0],
            "total_carts": total_carts,
            "completed_carts": completed
        },
        "product_combinations": [
            {
                "products": combo["product_combo"],
                "frequency": combo["frequency"]
            }
            for combo in product_combinations.collect()
        ],
        "abandoned_carts": [
            {
                "session_id": cart["session_id"],
                "products": cart["products"]
            }
            for cart in abandoned_carts.collect()
        ]
    }