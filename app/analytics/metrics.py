"""Metrics analytics module."""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from app.core.db_sync import events_col, sessions_col, products_col, users_col, carts_col
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

async def get_business_metrics(db, start_date: datetime, end_date: datetime, debug: bool = False) -> Dict[str, Any]:
    """Compute core business metrics from orders and events collections.

    Falls back to zeros when data is missing.
    """
    orders_col = None
    events_col = None
    dbg: Dict[str, Any] = {}

    try:
        if hasattr(db, "db"):
            try:
                orders_col = db.db["orders"]
            except Exception:
                orders_col = None
            try:
                events_col = db.db["events"]
            except Exception:
                events_col = None
    except Exception:
        orders_col = orders_col or None
        events_col = events_col or None

    revenue = 0.0
    orders = 0
    conversion_rate = 0.0
    visitors = 0
    total_sessions = 0
    total_events = 0
    last_event_ts = None
    # Normalize to UTC epoch seconds to avoid tz/localtime mismatches
    def to_epoch_s(dt: datetime) -> int:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    start_ts = to_epoch_s(start_date)
    end_ts = to_epoch_s(end_date)

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

            # If after all attempts the session count is still zero, fallback to events-based counting
            if total_sessions == 0 and events_col:
                time_filter = {
                    "$or": [
                        {"timestamp": {"$gte": start_ts, "$lte": end_ts}},
                        {"occurred_at": {"$gte": start_date, "$lte": end_date}},
                        {"occurred_at_iso": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}},
                    ]
                }
                try:
                    sess_ids = events_col.distinct("session_id", time_filter)
                    total_sessions = len([s for s in sess_ids if s])
                except Exception:
                    total_sessions = 0
                try:
                    user_ids = events_col.distinct("user_id", time_filter)
                    visitors = len([u for u in user_ids if u]) or visitors or 0
                except Exception:
                    visitors = visitors or 0

            # Dù sessions lấy từ sessions_col, ta vẫn có thể dùng events_col để thống kê total_events & last_event_ts
            if events_col:
                # Schema seed/ingest: mọi event đều có timestamp là epoch seconds (int)
                time_filter_events = {"timestamp": {"$gte": start_ts, "$lte": end_ts}}

                try:
                    total_events = events_col.count_documents(time_filter_events)
                except Exception:
                    total_events = total_events or 0

                # Lấy last_event_ts: dùng timestamp, fallback occurred_at/occurred_at_iso nếu có
                try:
                    doc_last = events_col.find(
                        time_filter_events,
                        {"timestamp": 1, "occurred_at": 1, "occurred_at_iso": 1},
                    ).sort([("timestamp", -1)]).limit(1)
                    docs = list(doc_last)
                    if docs:
                        d = docs[0]
                        if d.get("occurred_at") is not None:
                            dt = d.get("occurred_at")
                            try:
                                last_event_ts = dt.isoformat()
                            except Exception:
                                last_event_ts = str(dt)
                        elif d.get("occurred_at_iso"):
                            last_event_ts = str(d.get("occurred_at_iso"))
                        elif d.get("timestamp") is not None:
                            try:
                                import datetime as _dt
                                ts_val = d.get("timestamp")
                                ts = int(ts_val)
                                if ts > 1000000000000:
                                    ts = ts // 1000
                                last_event_ts = _dt.datetime.utcfromtimestamp(ts).isoformat()
                            except Exception:
                                last_event_ts = None
                except Exception:
                    last_event_ts = last_event_ts or None

        elif events_col:
            # Visitors and sessions estimated from events when sessions collection not available
            # Schema seed/ingest: timestamp epoch seconds
            time_filter = {"timestamp": {"$gte": start_ts, "$lte": end_ts}}
            user_ids = events_col.distinct("user_id", time_filter)
            visitors = len([u for u in user_ids if u])
            sess_ids = events_col.distinct("session_id", time_filter)
            total_sessions = len([s for s in sess_ids if s])
            # Tổng số events và last_event_ts khi không có sessions_col
            try:
                total_events = events_col.count_documents(time_filter)
            except Exception:
                total_events = total_events or 0
            try:
                doc_last = events_col.find(time_filter, {"timestamp": 1, "occurred_at": 1, "occurred_at_iso": 1}).sort([
                    ("occurred_at", -1),
                    ("timestamp", -1),
                ]).limit(1)
                docs = list(doc_last)
                if docs:
                    d = docs[0]
                    if d.get("occurred_at") is not None:
                        dt = d.get("occurred_at")
                        try:
                            last_event_ts = dt.isoformat()
                        except Exception:
                            last_event_ts = str(dt)
                    elif d.get("occurred_at_iso"):
                        last_event_ts = str(d.get("occurred_at_iso"))
                    elif d.get("timestamp") is not None:
                        try:
                            import datetime as _dt
                            ts_val = d.get("timestamp")
                            ts = int(ts_val)
                            if ts > 1000000000000:
                                ts = ts // 1000
                            last_event_ts = _dt.datetime.utcfromtimestamp(ts).isoformat()
                        except Exception:
                            last_event_ts = None
            except Exception:
                last_event_ts = last_event_ts or None

        # Conversions and revenue from purchase events (from events)
        if events_col:
            # Match purchase events across possible timestamp schemas:
            # - numeric epoch seconds in 'timestamp'
            # - numeric epoch milliseconds in 'timestamp' (string/number)
            # - datetime in 'occurred_at'
            # - string ISO in 'occurred_at_iso' with various timezone formats
            purchase_match = {
                "$and": [
                    {"$or": [
                        {"event_type": "purchase"},
                        {"$expr": {"$eq": [ {"$toLower": {"$trim": {"input": "$event_type"}}}, "purchase" ]}}
                    ]},
                    {"$or": [
                        # numeric epoch seconds
                        {"timestamp": {"$gte": start_ts, "$lte": end_ts}},
                        # numeric epoch milliseconds (timestamp stored as ms)
                        {"timestamp": {"$gte": start_ts * 1000, "$lte": end_ts * 1000}},
                        # datetime field
                        {"occurred_at": {"$gte": start_date, "$lte": end_date}},
                        # occurred_at_iso parsed to date
                        {"$expr": {"$and": [
                            {"$gte": [
                                {"$dateFromString": {"dateString": "$occurred_at_iso", "onError": None, "onNull": None}},
                                start_date
                            ]},
                            {"$lte": [
                                {"$dateFromString": {"dateString": "$occurred_at_iso", "onError": None, "onNull": None}},
                                end_date
                            ]}
                        ]}},
                        # timestamp stored as string seconds
                        {"$expr": {"$and": [
                            {"$gte": [ {"$toLong": "$timestamp"}, start_ts ]},
                            {"$lte": [ {"$toLong": "$timestamp"}, end_ts ]}
                        ]}},
                        # timestamp stored as string milliseconds
                        {"$expr": {"$and": [
                            {"$gte": [ {"$toLong": "$timestamp"}, start_ts * 1000 ]},
                            {"$lte": [ {"$toLong": "$timestamp"}, end_ts * 1000 ]}
                        ]}},
                    ]}
                ]
            }
            # Count conversions cheaply
            try:
                conv_count = events_col.count_documents(purchase_match)
            except Exception:
                # Fallback to find().count when count_documents fails under some mongos setups
                purchases_tmp = list(events_col.find(purchase_match, {"_id": 1}).limit(100000))
                conv_count = len(purchases_tmp)
            if orders == 0 and conv_count:
                orders = conv_count
            # Python-side sum to avoid aggregation operator compatibility issues
            try:
                # Project commonly used fields; avoid full documents
                purchases = list(events_col.find(
                    purchase_match,
                    {
                        "properties.total_amount": 1,
                        "properties.total": 1,
                        "properties.amount": 1,
                        "properties.value": 1,
                        "properties.cart_total": 1,
                        "properties.cart_items": 1,
                        "properties.product_details.price": 1,
                    }
                ))
                conv_count = len(purchases)
                if orders == 0 and conv_count:
                    orders = conv_count
                if debug:
                    dbg["conv_count"] = conv_count
                    # keep up to 3 sample projected docs (only properties subtree)
                    samples = []
                    for p in purchases[:3]:
                        props = p.get("properties", {}) or {}
                        samples.append({
                            "total_amount": props.get("total_amount"),
                            "total": props.get("total"),
                            "amount": props.get("amount"),
                            "value": props.get("value"),
                            "cart_total": props.get("cart_total"),
                            "price": (props.get("product_details") or {}).get("price") if isinstance(props.get("product_details"), dict) else None,
                            "cart_items": props.get("cart_items"),
                        })
                    dbg["purchase_samples"] = samples
                def to_float(x) -> float:
                    try:
                        return float(x)
                    except Exception:
                        try:
                            return float(str(x).replace(',', ''))
                        except Exception:
                            return 0.0
                def to_amount(p):
                    props = (p.get("properties") or {})
                    # Prefer explicit total fields
                    for k in ("total_amount","total","amount","value","cart_total"):
                        if k in props and props.get(k) not in (None,""):
                            return to_float(props.get(k))
                    # Fallback: price * cart_items when totals are missing
                    price = None
                    try:
                        pd = props.get("product_details") or {}
                        if isinstance(pd, dict):
                            price = pd.get("price")
                    except Exception:
                        price = None
                    items = props.get("cart_items") or 1
                    price_f = to_float(price) if price is not None else 0.0
                    items_f = to_float(items) if items is not None else 1.0
                    return price_f * items_f
                revenue_from_purchases = sum(to_amount(p) for p in purchases)
                if debug:
                    dbg["revenue_from_python"] = revenue_from_purchases
                if revenue_from_purchases:
                    revenue += revenue_from_purchases
            except Exception:
                pass

            # If still zero revenue and conv_count looks suspiciously low, run a robust aggregation fallback
            if revenue == 0.0:
                try:
                    pipeline = [
                        {"$match": {"$or": [
                            {"event_type": "purchase"},
                            {"$expr": {"$eq": [ {"$toLower": {"$trim": {"input": "$event_type"}}}, "purchase" ]}}
                        ]}},
                        {"$addFields": {
                            "_tLong": {"$toLong": "$timestamp"},
                            "_dt_iso": {"$dateFromString": {"dateString": "$occurred_at_iso", "onError": None, "onNull": None}},
                        }},
                        {"$addFields": {
                            "_ts_ms": {"$cond": [
                                {"$and": [ {"$gte": ["$_tLong", 1000000000000]}, {"$lte": ["$_tLong", 9999999999999]} ]},
                                "$_tLong",
                                {"$multiply": ["$_tLong", 1000]}
                            ]},
                        }},
                        {"$addFields": {
                            "event_dt": {"$ifNull": [
                                {"$toDate": "$occurred_at"},
                                {"$ifNull": ["$_dt_iso", {"$cond": [ {"$gt": ["$_tLong", None]}, {"$toDate": "$_ts_ms"}, None ]}]}
                            ]}
                        }},
                        {"$match": {"event_dt": {"$gte": start_date, "$lte": end_date}}},
                        {"$project": {
                            "ta": "$properties.total_amount",
                            "total": "$properties.total",
                            "amount": "$properties.amount",
                            "value": "$properties.value",
                            "cart_total": "$properties.cart_total",
                            "price": "$properties.product_details.price",
                            "items": "$properties.cart_items",
                        }},
                        {"$addFields": {
                            "picked": {"$ifNull": ["$ta", {"$ifNull": ["$total", {"$ifNull": ["$amount", {"$ifNull": ["$value", "$cart_total"]}]}]}]},
                            "priceItems": {"$multiply": [ {"$ifNull": ["$price", 0]}, {"$ifNull": ["$items", 1]} ]}
                        }},
                        {"$addFields": {"final": {"$cond": [ {"$gt": ["$picked", 0]}, "$picked", "$priceItems" ]}}},
                        {"$group": {"_id": None, "rev": {"$sum": "$final"}, "orders": {"$sum": 1}}}
                    ]
                    agg = list(events_col.aggregate(pipeline))
                    if agg:
                        revenue = float(agg[0].get("rev") or 0.0)
                        if not orders:
                            orders = int(agg[0].get("orders") or 0)
                        if debug:
                            dbg["revenue_from_pipeline"] = revenue
                except Exception:
                    pass
            conversions = conv_count
            conversion_rate = (conversions / visitors) if visitors else 0.0
    except Exception:
        # Keep safe defaults on any DB error
        pass

    average_order_value = (revenue / orders) if orders else 0.0
    result = {
        "revenue": revenue,
        "orders": orders,
        "average_order_value": average_order_value,
        "conversion_rate": conversion_rate,
        "total_users": visitors,
        "total_sessions": total_sessions,
        "total_events": total_events,
        "last_event_ts": last_event_ts,
    }
    if debug:
        result["_debug"] = dbg
    return result

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