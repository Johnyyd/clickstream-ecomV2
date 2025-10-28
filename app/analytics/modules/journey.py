"""
Customer Journey Analytics Module
Analyzes customer journey patterns and conversion paths
"""
from typing import Dict, Any, Optional

from app.core.spark import spark_manager
from ..base import AnalyticsModule

class JourneyAnalytics(AnalyticsModule):
    """Analyzes customer journey patterns"""
    
    def __init__(self):
        super().__init__("Journey Analysis", parallel=True)
        
    def run_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """
        Run customer journey analysis
        
        Analyzes:
        - Conversion paths
        - Drop-off points
        - Path length impact
        - Channel effectiveness
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
        
        # Analyze conversion paths
        paths_df = spark.sql("""
            WITH journey_steps AS (
                SELECT 
                    session_id,
                    ARRAY_JOIN(
                        COLLECT_LIST(
                            CONCAT(
                                event_type,
                                CASE 
                                    WHEN properties.path IS NOT NULL 
                                    THEN CONCAT(':', properties.path)
                                    ELSE ''
                                END
                            )
                        ),
                        ' > '
                    ) as journey_path,
                    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as converted
                FROM (
                    SELECT *
                    FROM filtered_events
                    ORDER BY session_id, timestamp
                )
                GROUP BY session_id
            )
            SELECT
                journey_path,
                COUNT(*) as frequency,
                SUM(converted) as conversions,
                AVG(converted) as conversion_rate
            FROM journey_steps
            GROUP BY journey_path
            HAVING frequency >= 5
            ORDER BY frequency DESC
        """)
        
        # Analyze drop-off points
        dropoff_df = spark.sql("""
            WITH journey_steps AS (
                SELECT
                    session_id,
                    event_type,
                    properties.path,
                    ROW_NUMBER() OVER (
                        PARTITION BY session_id 
                        ORDER BY timestamp
                    ) as step_number,
                    LEAD(event_type) OVER (
                        PARTITION BY session_id 
                        ORDER BY timestamp
                    ) as next_event
                FROM filtered_events
            )
            SELECT
                event_type,
                path,
                COUNT(*) as occurrences,
                SUM(CASE WHEN next_event IS NULL THEN 1 ELSE 0 END) as dropoffs,
                ROUND(
                    SUM(CASE WHEN next_event IS NULL THEN 1 ELSE 0 END) * 100.0 / 
                    COUNT(*),
                    2
                ) as dropoff_rate
            FROM journey_steps
            GROUP BY event_type, path
            HAVING dropoffs > 0
            ORDER BY dropoff_rate DESC
        """)
        
        # Analyze path length impact
        length_df = spark.sql("""
            WITH journey_metrics AS (
                SELECT
                    session_id,
                    COUNT(*) as steps,
                    COUNT(DISTINCT event_type) as unique_steps,
                    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as converted
                FROM filtered_events
                GROUP BY session_id
            )
            SELECT
                CASE
                    WHEN steps < 5 THEN 'Very Short (1-4)'
                    WHEN steps < 10 THEN 'Short (5-9)'
                    WHEN steps < 20 THEN 'Medium (10-19)'
                    ELSE 'Long (20+)'
                END as journey_length,
                COUNT(*) as sessions,
                AVG(steps) as avg_steps,
                AVG(unique_steps) as avg_unique_steps,
                AVG(converted) as conversion_rate
            FROM journey_metrics
            GROUP BY
                CASE
                    WHEN steps < 5 THEN 'Very Short (1-4)'
                    WHEN steps < 10 THEN 'Short (5-9)'
                    WHEN steps < 20 THEN 'Medium (10-19)'
                    ELSE 'Long (20+)'
                END
            ORDER BY avg_steps
        """)
        
        # Channel effectiveness
        channel_df = spark.sql("""
            WITH channel_journeys AS (
                SELECT
                    session_id,
                    FIRST_VALUE(properties.source) OVER (
                        PARTITION BY session_id
                        ORDER BY timestamp
                    ) as entry_channel,
                    COUNT(*) as steps,
                    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as converted
                FROM filtered_events
                GROUP BY session_id
            )
            SELECT
                entry_channel,
                COUNT(*) as sessions,
                AVG(steps) as avg_journey_length,
                SUM(converted) as conversions,
                AVG(converted) as conversion_rate
            FROM channel_journeys
            GROUP BY entry_channel
            ORDER BY sessions DESC
        """)
        
        return {
            "conversion_paths": paths_df.toPandas().to_dict('records'),
            "dropoff_points": dropoff_df.toPandas().to_dict('records'),
            "path_length_impact": length_df.toPandas().to_dict('records'),
            "channel_effectiveness": channel_df.toPandas().to_dict('records')
        }