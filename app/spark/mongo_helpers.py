"""
MongoDB Helper Functions for Spark Analytics
Optimized batch loading and filtering to prevent cursor timeouts
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.db_sync import events_col, users_col

logger = logging.getLogger(__name__)


def load_events_batch(
    pipeline: List[Dict], batch_size: int = 5000, max_time_ms: int = 300000  # 5 minutes
) -> List[Dict]:
    """
    Load events from MongoDB with optimized cursor handling.

    Prevents cursor timeout by:
    - Using batchSize to control memory
    - Enabling allowDiskUse for large sorts
    - Setting reasonable timeout

    Args:
        pipeline: MongoDB aggregation pipeline
        batch_size: Number of documents per batch (default: 5000)
        max_time_ms: Maximum query time in milliseconds (default: 300000 = 5 min)

    Returns:
        List of event documents
    """
    events = []
    cursor = None

    try:
        cursor = events_col().aggregate(
            pipeline,
            batchSize=batch_size,
            allowDiskUse=True,  # Allow MongoDB to use disk for large operations
            maxTimeMS=max_time_ms,
        )

        for doc in cursor:
            events.append(doc)

        logger.info(f"[MongoHelper] Loaded {len(events)} events successfully")
        return events

    except Exception as e:
        logger.error(f"[MongoHelper] Error loading events: {e}")
        raise
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass


def build_filter_pipeline(
    username: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    segment: Optional[str] = None,
    channel: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    additional_filters: Optional[Dict] = None,
) -> List[Dict]:
    """
    Build MongoDB aggregation pipeline with common filters.

    Args:
        username: Filter by username (looks up user_id)
        date_from: Start date filter (timestamp >= date_from)
        date_to: End date filter (timestamp <= date_to)
        segment: User segment filter ('all' = no filter)
        channel: Traffic channel filter (matches properties.referrer)
        event_types: List of event types to include
        additional_filters: Additional MongoDB match conditions

    Returns:
        MongoDB aggregation pipeline
    """
    pipeline = []
    match_conditions = {}

    # User filter
    if username:
        user = users_col().find_one({"username": username})
        if user:
            # Check if admin - don't filter if admin
            if user.get("role") != "admin":
                match_conditions["user_id"] = user["_id"]
            else:
                logger.info(
                    f"[MongoHelper] User '{username}' is admin - querying all users"
                )
        else:
            logger.warning(f"[MongoHelper] User '{username}' not found")
            return []  # Return empty pipeline if user doesn't exist

    # Date range filter
    if date_from or date_to:
        timestamp_filter = {}
        if date_from:
            timestamp_filter["$gte"] = int(date_from.timestamp())
        if date_to:
            timestamp_filter["$lte"] = int(date_to.timestamp())
        match_conditions["timestamp"] = timestamp_filter

    # Event type filter
    if event_types:
        match_conditions["event_type"] = {"$in": event_types}

    # Additional custom filters
    if additional_filters:
        match_conditions.update(additional_filters)

    # Add match stage if we have conditions
    if match_conditions:
        pipeline.append({"$match": match_conditions})

    # Channel filter (in properties.referrer)
    # Note: This is separate because it's a nested field
    if channel and channel != "all":
        pipeline.append(
            {
                "$match": {
                    "properties.referrer": {
                        "$regex": channel,
                        "$options": "i",  # Case insensitive
                    }
                }
            }
        )

    # Segment filter (requires lookup to user_segments collection)
    if segment and segment != "all":
        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "user_segments",
                        "localField": "user_id",
                        "foreignField": "user_id",
                        "as": "segment_data",
                    }
                },
                {"$match": {"segment_data.segment": segment}},
                {"$project": {"segment_data": 0}},  # Remove temporary field
            ]
        )

    logger.info(f"[MongoHelper] Built pipeline with {len(pipeline)} stages")
    return pipeline


def load_events_filtered(
    username: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    segment: Optional[str] = None,
    channel: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    additional_filters: Optional[Dict] = None,
    batch_size: int = 5000,
) -> List[Dict]:
    """
    Convenience function combining filter building and batch loading.

    One-stop shop for loading filtered events with optimized cursor handling.
    Use this in all Spark modules for consistent behavior.

    Example:
        events = load_events_filtered(
            username="alice",
            date_from=datetime(2026, 1, 1),
            date_to=datetime(2026, 1, 31),
            segment="high_value",
            channel="google"
        )
    """
    pipeline = build_filter_pipeline(
        username=username,
        date_from=date_from,
        date_to=date_to,
        segment=segment,
        channel=channel,
        event_types=event_types,
        additional_filters=additional_filters,
    )

    if not pipeline:
        logger.warning("[MongoHelper] Empty pipeline - no results will be returned")
        return []

    return load_events_batch(pipeline, batch_size=batch_size)


def get_last_processed_timestamp(module_name: str) -> Optional[int]:
    """
    Get timestamp of last successful analytics run for incremental processing.

    Args:
        module_name: Unique identifier for analytics module

    Returns:
        Unix timestamp of last run, or None if never run
    """
    from app.core.db_sync import db

    metadata_col = db["analytics_metadata"]
    doc = metadata_col.find_one({"module": module_name})
    return doc.get("last_processed_ts") if doc else None


def update_last_processed_timestamp(module_name: str, timestamp: int):
    """
    Update last processed timestamp for incremental processing.

    Args:
        module_name: Unique identifier for analytics module
        timestamp: Unix timestamp to record
    """
    from app.core.db_sync import db
    from datetime import datetime

    metadata_col = db["analytics_metadata"]
    metadata_col.update_one(
        {"module": module_name},
        {"$set": {"last_processed_ts": timestamp, "updated_at": datetime.now()}},
        upsert=True,
    )
    logger.info(
        f"[MongoHelper] Updated last_processed_ts for '{module_name}': {timestamp}"
    )


def add_incremental_filter(pipeline: List[Dict], module_name: str) -> List[Dict]:
    """
    Add incremental filter to pipeline based on last run timestamp.

    Args:
        pipeline: Existing pipeline
        module_name: Module name to look up last run

    Returns:
        Modified pipeline with timestamp filter prepended
    """
    last_ts = get_last_processed_timestamp(module_name)

    if last_ts:
        logger.info(
            f"[MongoHelper] Incremental mode: processing events after {last_ts}"
        )
        # Prepend timestamp filter
        pipeline.insert(0, {"$match": {"timestamp": {"$gt": last_ts}}})
    else:
        logger.info(
            f"[MongoHelper] Full refresh mode: no previous run found for '{module_name}'"
        )

    return pipeline
