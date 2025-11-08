"""
traffic_utils.py - Shared helpers for traffic source normalization in Spark analytics
"""
from typing import Optional

def create_events_enriched_view(spark, source_view: str = "events", target_view: str = "events_enriched") -> None:
    """
    Create or replace a temp view with a consistent `traffic_source` column derived from
    normalized `referrer` and `source` columns.

    Assumes the `source_view` contains at least the columns: referrer, source, session_id, user_id, event_type, page, timestamp.
    """
    spark.sql(f"""
        CREATE OR REPLACE TEMP VIEW {target_view} AS
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
        FROM {source_view}
    """)
