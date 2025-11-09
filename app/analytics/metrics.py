"""Metrics analytics module."""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

def get_user_metrics(user_id: str) -> Dict[str, Any]:
    """Get metrics for a specific user."""
    return {
        "user_id": user_id,
        "engagement_score": 0.0,
        "lifetime_value": 0.0,
        "activity_metrics": {}
    }

def get_session_metrics(session_id: str) -> Dict[str, Any]:
    """Get metrics for a specific session."""
    return {
        "session_id": session_id,
        "duration": 0.0,
        "page_views": 0,
        "events": []
    }

def get_conversion_metrics(timeframe: str = "7d") -> Dict[str, Any]:
    """Get conversion metrics."""
    return {
        "overall_rate": 0.0,
        "by_source": {},
        "by_segment": {}
    }

def get_engagement_metrics() -> Dict[str, Any]:
    """Get engagement metrics."""
    return {
        "average_session_duration": 0.0,
        "pages_per_session": 0.0,
        "bounce_rate": 0.0
    }

# New implementations used by API endpoints

async def get_business_metrics(db, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Compute core business metrics from orders and events collections.

    Falls back to zeros when data is missing.
    """
    orders_col = None
    events_col = None
    if hasattr(db, "db"):
        try:
            orders_col = db.db["orders"]
        except Exception:
            orders_col = None
        try:
            events_col = db.db["events"]
        except Exception:
            events_col = None

    revenue = 0.0
    orders = 0
    conversion_rate = 0.0
    visitors = 0
    total_sessions = 0
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())

    try:
        # Prefer accurate counts from 'sessions' collection when available
        sessions_col = None
        if hasattr(db, "db"):
            try:
                # PyMongo Database does not support .get; use direct indexing
                sessions_col = db.db["sessions"]
            except Exception:
                sessions_col = None

        if orders_col:
            cursor = orders_col.find({
                "created_at": {"$gte": start_date, "$lte": end_date}
            }, {"total": 1})
            for o in cursor:
                orders += 1
                try:
                    revenue += float(o.get("total", 0) or 0)
                except Exception:
                    pass

        if sessions_col:
            # Use first_event_at/last_event_at window for session counts
            used_string_fallback = False
            try:
                total_sessions = sessions_col.count_documents({
                    "first_event_at": {"$gte": start_date, "$lte": end_date}
                })
                # If zero, try last_event_at
                if total_sessions == 0:
                    total_sessions = sessions_col.count_documents({
                        "last_event_at": {"$gte": start_date, "$lte": end_date}
                    })
            except Exception:
                total_sessions = 0
            # If still zero, fallback for string dates using $toDate
            if total_sessions == 0:
                try:
                    pipeline = [
                        {"$match": {"$expr": {"$and": [
                            {"$gte": [{"$toDate": "$first_event_at"}, start_date]},
                            {"$lte": [{"$toDate": "$first_event_at"}, end_date]},
                        ]}}},
                        {"$count": "n"}
                    ]
                    res = list(sessions_col.aggregate(pipeline))
                    total_sessions = int(res[0]["n"]) if res else 0
                    used_string_fallback = True
                except Exception:
                    pass
            # Visitors (distinct user_id) under the same window
            try:
                if not used_string_fallback:
                    uids = sessions_col.distinct("user_id", {
                        "first_event_at": {"$gte": start_date, "$lte": end_date}
                    })
                    visitors = len([u for u in uids if u])
                else:
                    pipeline_u = [
                        {"$match": {"$expr": {"$and": [
                            {"$gte": [{"$toDate": "$first_event_at"}, start_date]},
                            {"$lte": [{"$toDate": "$first_event_at"}, end_date]},
                        ]}}},
                        {"$group": {"_id": "$user_id"}},
                        {"$count": "n"}
                    ]
                    res_u = list(sessions_col.aggregate(pipeline_u))
                    visitors = int(res_u[0]["n"]) if res_u else 0
            except Exception:
                visitors = visitors or 0

        elif events_col:
            # Visitors and sessions estimated from events when sessions collection not available
            user_ids = events_col.distinct("user_id", {
                "timestamp": {"$gte": start_ts, "$lte": end_ts}
            })
            visitors = len([u for u in user_ids if u])
            sess_ids = events_col.distinct("session_id", {
                "timestamp": {"$gte": start_ts, "$lte": end_ts}
            })
            total_sessions = len([s for s in sess_ids if s])

        # Conversions and revenue from purchase events (from events)
        if events_col:
            purchases = list(events_col.find({
                "event_type": "purchase",
                "timestamp": {"$gte": start_ts, "$lte": end_ts}
            }, {"properties.total_amount": 1}))
            conv_count = len(purchases)
            if orders == 0 and conv_count:
                orders = conv_count
            try:
                revenue_from_purchases = sum(float((p.get("properties") or {}).get("total_amount", 0) or 0) for p in purchases)
                if revenue_from_purchases:
                    revenue += revenue_from_purchases
            except Exception:
                pass
            conversions = conv_count
            conversion_rate = (conversions / visitors) if visitors else 0.0
    except Exception:
        # Keep safe defaults on any DB error
        pass

    average_order_value = (revenue / orders) if orders else 0.0
    return {
        "revenue": revenue,
        "orders": orders,
        "average_order_value": average_order_value,
        "conversion_rate": conversion_rate,
        "total_users": visitors,
        "total_sessions": total_sessions,
    }

async def get_behavior_metrics(db, start_date: datetime, end_date: datetime, segment: Optional[str] = None) -> Dict[str, Any]:
    """Compute user behavior metrics from events collection.

    Returns defaults if data missing.
    """
    events_col = db.db.get("events") if hasattr(db, "db") else None
    sessions = 0
    page_views = 0
    bounce_rate = 0.0
    try:
        if events_col:
            query = {"timestamp": {"$gte": start_date, "$lte": end_date}}
            if segment:
                query["segment"] = segment
            page_views = events_col.count_documents({**query, "event_type": "page_view"})
            sessions_docs = events_col.distinct("session_id", query)
            sessions = len([s for s in sessions_docs if s])
            bounces = events_col.count_documents({**query, "event_type": "bounce"})
            bounce_rate = (bounces / sessions) if sessions else 0.0
    except Exception:
        pass
    return {
        "sessions": sessions,
        "page_views": page_views,
        "bounce_rate": bounce_rate,
    }

async def get_performance_metrics(db, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Compute simple system performance metrics using an events/errors collection when present."""
    logs_col = None
    if hasattr(db, "db"):
        try:
            logs_col = db.db["logs"]
        except Exception:
            logs_col = None
    successes = 0
    errors = 0
    try:
        if logs_col:
            successes = logs_col.count_documents({
                "level": "info",
                "timestamp": {"$gte": start_date, "$lte": end_date}
            })
            errors = logs_col.count_documents({
                "level": {"$in": ["error", "exception"]},
                "timestamp": {"$gte": start_date, "$lte": end_date}
            })
    except Exception:
        pass
    total = successes + errors
    success_rate = (successes / total) if total else 0.0
    return {
        "success_rate": success_rate,
        "success_count": successes,
        "error_count": errors,
    }

async def get_trends(db, metrics: List[str], period: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Return very simple trend series per metric name using events/orders counts.

    This is a placeholder DB-backed implementation to avoid 500s.
    """
    events_col = None
    orders_col = None
    if hasattr(db, "db"):
        try:
            events_col = db.db["events"]
        except Exception:
            events_col = None
        try:
            orders_col = db.db["orders"]
        except Exception:
            orders_col = None
    series: List[Dict[str, Any]] = []

    # Determine bucket size
    delta = timedelta(days=1)
    if period == "weekly":
        delta = timedelta(weeks=1)
    elif period == "monthly":
        delta = timedelta(days=30)

    # Build buckets
    buckets = []
    t = start_date
    while t <= end_date:
        buckets.append(t)
        t = t + delta

    def count_in_range(col, query_extra: Dict[str, Any]) -> List[int]:
        vals: List[int] = []
        for i, bt in enumerate(buckets):
            bt_end = buckets[i+1] if i+1 < len(buckets) else end_date
            q = {
                "timestamp": {"$gte": bt, "$lte": bt_end},
                **query_extra,
            }
            try:
                vals.append(col.count_documents(q))
            except Exception:
                vals.append(0)
        return vals

    for m in metrics or []:
        data = []
        if m in ("page_views", "sessions", "events") and events_col:
            data = count_in_range(events_col, {} if m == "events" else {"event_type": "page_view"})
        elif m in ("orders", "purchases") and orders_col:
            # assume orders have created_at field
            vals: List[int] = []
            for i, bt in enumerate(buckets):
                bt_end = buckets[i+1] if i+1 < len(buckets) else end_date
                try:
                    vals.append(orders_col.count_documents({
                        "created_at": {"$gte": bt, "$lte": bt_end}
                    }))
                except Exception:
                    vals.append(0)
            data = vals
        else:
            data = [0 for _ in buckets]
        series.append({"name": m, "data": data})

    return series