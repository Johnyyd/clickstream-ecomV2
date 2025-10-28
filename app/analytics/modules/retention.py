"""
Retention Analytics Module
Analyzes customer retention and cohort behavior
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.spark import spark_manager
from ..base import AnalyticsModule

class RetentionAnalytics(AnalyticsModule):
    """Analyzes customer retention patterns"""
    
    def __init__(self):
        super().__init__("Retention Analysis", parallel=True)
        
    def run_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """
        Run retention analysis
        
        Analyzes:
        - Cohort retention rates
        - Engagement over time
        - Customer lifetime 
        - Activity patterns
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
        
        # Calculate cohort retention
        retention_df = spark.sql("""
            WITH first_activity AS (
                SELECT
                    user_id,
                    DATE_TRUNC('month', MIN(timestamp)) as cohort_month
                FROM filtered_events
                GROUP BY user_id
            ),
            monthly_activity AS (
                SELECT
                    fa.user_id,
                    fa.cohort_month,
                    DATE_TRUNC('month', e.timestamp) as activity_month,
                    MONTHS_BETWEEN(
                        DATE_TRUNC('month', e.timestamp),
                        fa.cohort_month
                    ) as month_number
                FROM first_activity fa
                JOIN filtered_events e ON fa.user_id = e.user_id
            )
            SELECT
                cohort_month,
                month_number,
                COUNT(DISTINCT user_id) as active_users,
                COUNT(DISTINCT CASE WHEN month_number = 0 THEN user_id END) as cohort_size,
                ROUND(
                    COUNT(DISTINCT user_id) * 100.0 / 
                    FIRST_VALUE(COUNT(DISTINCT user_id)) OVER (
                        PARTITION BY cohort_month 
                        ORDER BY month_number
                    ),
                    2
                ) as retention_rate
            FROM monthly_activity
            GROUP BY cohort_month, month_number
            HAVING month_number >= 0
            ORDER BY cohort_month, month_number
        """)
        
        # Engagement trends
        engagement_df = spark.sql("""
            WITH user_engagement AS (
                SELECT
                    user_id,
                    DATE_TRUNC('day', timestamp) as day,
                    COUNT(*) as events,
                    COUNT(DISTINCT event_type) as unique_actions,
                    SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as purchases
                FROM filtered_events
                GROUP BY user_id, DATE_TRUNC('day', timestamp)
            )
            SELECT
                day,
                COUNT(DISTINCT user_id) as active_users,
                AVG(events) as avg_events_per_user,
                AVG(unique_actions) as avg_unique_actions,
                SUM(purchases) as total_purchases
            FROM user_engagement
            GROUP BY day
            ORDER BY day
        """)
        
        # Customer lifetime analysis
        lifetime_df = spark.sql("""
            WITH user_activity AS (
                SELECT
                    user_id,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen,
                    COUNT(DISTINCT DATE_TRUNC('day', timestamp)) as active_days,
                    COUNT(*) as total_events,
                    SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as purchases
                FROM filtered_events
                GROUP BY user_id
            )
            SELECT
                CASE 
                    WHEN DATEDIFF(last_seen, first_seen) < 30 THEN 'New'
                    WHEN DATEDIFF(last_seen, first_seen) < 90 THEN 'Growing'
                    ELSE 'Established'
                END as customer_stage,
                COUNT(*) as users,
                AVG(DATEDIFF(last_seen, first_seen)) as avg_lifetime_days,
                AVG(active_days) as avg_active_days,
                AVG(total_events) as avg_total_events,
                AVG(purchases) as avg_purchases
            FROM user_activity
            GROUP BY
                CASE 
                    WHEN DATEDIFF(last_seen, first_seen) < 30 THEN 'New'
                    WHEN DATEDIFF(last_seen, first_seen) < 90 THEN 'Growing'
                    ELSE 'Established'
                END
        """)
        
        # Activity patterns
        patterns_df = spark.sql("""
            SELECT
                user_id,
                COUNT(*) as total_events,
                COUNT(DISTINCT DATE_TRUNC('day', timestamp)) as active_days,
                COUNT(DISTINCT event_type) as action_types,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as purchases,
                AVG(CASE 
                    WHEN event_type = 'purchase' 
                    THEN CAST(properties.price AS DECIMAL(10,2))
                    ELSE NULL
                END) as avg_purchase_value
            FROM filtered_events
            GROUP BY user_id
            ORDER BY total_events DESC
            LIMIT 1000
        """)
        
        return {
            "cohort_retention": retention_df.toPandas().to_dict('records'),
            "engagement_trends": engagement_df.toPandas().to_dict('records'),
            "customer_lifetime": lifetime_df.toPandas().to_dict('records'),
            "activity_patterns": patterns_df.toPandas().to_dict('records')
        }