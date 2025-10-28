"""
Cart Analytics Module
Analyzes shopping cart behavior and abandonment
"""
from typing import Dict, Any, Optional

from app.core.spark import spark_manager
from ..base import AnalyticsModule

class CartAnalytics(AnalyticsModule):
    """Analyzes cart behavior and abandonment patterns"""
    
    def __init__(self):
        super().__init__("Cart Abandonment Analysis", parallel=True)
        
    def run_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """
        Analyze cart abandonment patterns
        
        Analyzes:
        - Abandonment rates
        - Cart value distribution
        - Recovery opportunities
        - Time to purchase/abandon
        """
        spark = spark_manager.session
        
        # Register base view
        events_df = spark.sql("""
            SELECT * FROM events 
            WHERE flag.noisy = false
            AND properties.source NOT IN ('simulation', 'basic_sim', 'seed_demo')
        """)
        
        if username:
            events_df = events_df.filter(f"user_id = '{username}'")
        if limit:
            events_df = events_df.limit(limit)
            
        events_df.createOrReplaceTempView("filtered_events")
        
        # Cart abandonment rates
        abandonment_df = spark.sql("""
            WITH cart_sessions AS (
                SELECT
                    session_id,
                    MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) as had_cart,
                    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as purchased
                FROM filtered_events
                GROUP BY session_id
            )
            SELECT
                COUNT(*) as total_sessions,
                SUM(had_cart) as cart_sessions,
                SUM(purchased) as purchase_sessions,
                AVG(CASE WHEN had_cart = 1 THEN purchased ELSE NULL END) as conversion_rate,
                1 - AVG(CASE WHEN had_cart = 1 THEN purchased ELSE NULL END) as abandonment_rate
            FROM cart_sessions
        """)
        
        # Cart value distribution
        value_df = spark.sql("""
            WITH cart_values AS (
                SELECT
                    session_id,
                    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as purchased,
                    SUM(CASE 
                        WHEN event_type = 'add_to_cart' 
                        THEN CAST(properties.price AS DECIMAL(10,2))
                        ELSE 0 
                    END) as cart_value
                FROM filtered_events
                GROUP BY session_id
                HAVING cart_value > 0
            )
            SELECT
                CASE
                    WHEN cart_value < 50 THEN 'Under $50'
                    WHEN cart_value < 100 THEN '$50-$100'
                    WHEN cart_value < 200 THEN '$100-$200'
                    ELSE 'Over $200'
                END as value_range,
                COUNT(*) as sessions,
                AVG(purchased) as conversion_rate,
                AVG(cart_value) as avg_value
            FROM cart_values
            GROUP BY 
                CASE
                    WHEN cart_value < 50 THEN 'Under $50'
                    WHEN cart_value < 100 THEN '$50-$100'
                    WHEN cart_value < 200 THEN '$100-$200'
                    ELSE 'Over $200'
                END
            ORDER BY avg_value
        """)
        
        # Recovery opportunities
        recovery_df = spark.sql("""
            WITH abandoned_carts AS (
                SELECT
                    user_id,
                    session_id,
                    MAX(properties.price) as cart_value,
                    MAX(timestamp) as last_activity
                FROM filtered_events
                WHERE event_type = 'add_to_cart'
                AND session_id NOT IN (
                    SELECT DISTINCT session_id
                    FROM filtered_events
                    WHERE event_type = 'purchase'
                )
                GROUP BY user_id, session_id
            )
            SELECT
                user_id,
                COUNT(*) as abandoned_carts,
                AVG(cart_value) as avg_cart_value,
                MAX(last_activity) as latest_abandonment
            FROM abandoned_carts
            GROUP BY user_id
            HAVING COUNT(*) > 1
            ORDER BY avg_cart_value DESC
            LIMIT 100
        """)
        
        # Time to purchase analysis
        timing_df = spark.sql("""
            WITH cart_timing AS (
                SELECT
                    session_id,
                    MIN(CASE WHEN event_type = 'add_to_cart' THEN timestamp END) as first_cart,
                    MAX(CASE WHEN event_type = 'purchase' THEN timestamp END) as purchase_time
                FROM filtered_events
                GROUP BY session_id
                HAVING first_cart IS NOT NULL
            )
            SELECT
                CASE WHEN purchase_time IS NOT NULL THEN 'Purchased' ELSE 'Abandoned' END as outcome,
                COUNT(*) as sessions,
                AVG(
                    UNIX_TIMESTAMP(
                        COALESCE(purchase_time, MAX(timestamp)) 
                    ) - UNIX_TIMESTAMP(first_cart)
                ) as avg_time_seconds
            FROM cart_timing
            LEFT JOIN filtered_events ON cart_timing.session_id = filtered_events.session_id
            GROUP BY 
                CASE WHEN purchase_time IS NOT NULL THEN 'Purchased' ELSE 'Abandoned' END
        """)
        
        return {
            "abandonment_stats": abandonment_df.toPandas().to_dict('records')[0],
            "value_distribution": value_df.toPandas().to_dict('records'),
            "recovery_opportunities": recovery_df.toPandas().to_dict('records'),
            "timing_analysis": timing_df.toPandas().to_dict('records')
        }