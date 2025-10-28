"""
SEO Analytics Module
Analyzes traffic sources and SEO performance
"""
from typing import Dict, Any, Optional

from app.core.spark import spark_manager
from ..base import AnalyticsModule

class SEOAnalytics(AnalyticsModule):
    """Analyzes SEO and traffic source data"""
    
    def __init__(self):
        super().__init__("SEO & Traffic Analysis", parallel=False)
        
    def run_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """
        Run SEO analysis
        
        Analyzes:
        - Traffic by source
        - Landing page performance 
        - Conversion by source
        - Hourly traffic patterns
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
        
        # Traffic by source
        traffic_df = spark.sql("""
            SELECT 
                properties.source,
                COUNT(*) as visits,
                COUNT(DISTINCT user_id) as unique_visitors,
                COUNT(DISTINCT session_id) as sessions
            FROM filtered_events
            WHERE event_type = 'page_view'
            GROUP BY properties.source
            ORDER BY visits DESC
        """)
        
        # Landing pages
        landing_df = spark.sql("""
            WITH session_starts AS (
                SELECT 
                    session_id,
                    MIN(timestamp) as session_start,
                    FIRST_VALUE(properties.path) OVER (
                        PARTITION BY session_id 
                        ORDER BY timestamp
                    ) as landing_page
                FROM filtered_events
                GROUP BY session_id
            )
            SELECT
                landing_page,
                COUNT(*) as sessions,
                COUNT(DISTINCT user_id) as unique_visitors,
                AVG(CAST(converted AS INT)) as conversion_rate
            FROM session_starts
            GROUP BY landing_page
            ORDER BY sessions DESC
        """)
        
        # Conversion by source
        conversion_df = spark.sql("""
            SELECT
                properties.source,
                COUNT(DISTINCT user_id) as users,
                SUM(CAST(converted AS INT)) as conversions,
                AVG(CAST(converted AS INT)) as conversion_rate
            FROM filtered_events
            WHERE event_type = 'conversion'
            GROUP BY properties.source
            ORDER BY conversions DESC
        """)
        
        # Hourly traffic
        hourly_df = spark.sql("""
            SELECT 
                HOUR(timestamp) as hour,
                COUNT(*) as visits,
                COUNT(DISTINCT user_id) as unique_visitors
            FROM filtered_events
            WHERE event_type = 'page_view'
            GROUP BY HOUR(timestamp)
            ORDER BY hour
        """)
        
        return {
            "traffic_by_source": traffic_df.toPandas().to_dict('records'),
            "landing_pages": landing_df.toPandas().to_dict('records'),
            "conversion_by_source": conversion_df.toPandas().to_dict('records'),
            "hourly_traffic": hourly_df.toPandas().to_dict('records')
        }