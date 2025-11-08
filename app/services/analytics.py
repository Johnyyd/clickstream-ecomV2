"""
Analytics service functions
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional

async def get_user_journey_analysis(db, start_date: datetime, end_date: datetime, user_id: Optional[str] = None):
    """
    Analyze user journey patterns
    """
    # Seeded events store timestamp as epoch seconds (int), not datetime
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    query = {
        "timestamp": {
            "$gte": start_ts,
            "$lte": end_ts
        }
    }
    if user_id:
        query["user_id"] = user_id
        
    events_col = db.db["events"]
    events = list(events_col.find(query))

    # Safe defaults for JourneyAnalysis (latest model version)
    session_metrics = {
        "total_sessions": 0,
        "avg_session_duration": 0.0,
        "bounce_rate": 0.0,
        "pages_per_session": 0.0,
        "conversion_rate": 0.0,
    }
    top_paths: list[dict] = []
    conversion_funnel: list[dict] = []
    popular_entry_points: list[dict] = []
    popular_exit_points: list[dict] = []
    recommendations: list[str] = []

    # Minimal funnel based on counts
    try:
        total_views = sum(1 for e in events if e.get("event_type") in ("pageview", "search"))
        total_add = sum(1 for e in events if e.get("event_type") == "add_to_cart")
        total_checkout = sum(1 for e in events if e.get("event_type") == "checkout")
        total_purchase = sum(1 for e in events if e.get("event_type") == "purchase")
        steps = [
            {"name": "Views", "count": total_views, "rate": 1.0, "drop_off": 0.0},
            {"name": "Add to Cart", "count": total_add, "rate": (total_add/total_views) if total_views else 0.0},
            {"name": "Checkout", "count": total_checkout, "rate": (total_checkout/total_add) if total_add else 0.0},
            {"name": "Purchase", "count": total_purchase, "rate": (total_purchase/total_checkout) if total_checkout else 0.0},
        ]
        conversion_funnel = steps
    except Exception:
        pass

    return {
        "session_metrics": session_metrics,
        "top_paths": top_paths,
        "conversion_funnel": conversion_funnel,
        "time_to_convert": None,
        "popular_entry_points": popular_entry_points,
        "popular_exit_points": popular_exit_points,
        "recommendations": recommendations,
        # SPA compat minimal funnel field
        "funnel": {"steps": conversion_funnel} if conversion_funnel else None,
    }

async def get_cart_analysis(db, start_date: datetime, end_date: datetime):
    """
    Analyze cart behavior
    """
    events_col = db.db["events"]
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    cart_events = list(events_col.find({
        "event_type": {"$in": ["add_to_cart", "remove_from_cart", "checkout"]},
        "timestamp": {"$gte": start_ts, "$lte": end_ts}
    }))
    
    # Process cart data (safe defaults)
    total_carts = 0
    active_carts = 0
    abandoned_carts = 0
    total_cart_value = 0.0
    items_per_cart: list[int] = []
    # Note: Without a cart grouping, we can't aggregate accurately; keep zeros

    avg_items_per_cart = (sum(items_per_cart) / len(items_per_cart)) if items_per_cart else 0.0
    avg_cart_value = (total_cart_value / total_carts) if total_carts else 0.0
    abandonment_rate = (abandoned_carts / total_carts) if total_carts else 0.0

    # Minimal channels aggregation using referrer mapping similar to SEO
    def to_channel(ref: str) -> str:
        r = (ref or "").lower()
        if not r or r == "direct":
            return "direct"
        if any(k in r for k in ("google", "bing")):
            return "seo"
        if any(k in r for k in ("facebook", "twitter", "instagram")):
            return "social"
        if "ads" in r:
            return "paid"
        return "referral"

    # Build per-session channel using first event's referrer if available
    channels: Dict[str, Any] = {}
    try:
        # Count checkouts and purchases per channel
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        sess_checkout: Dict[str, int] = {}
        sess_purchase: Dict[str, int] = {}
        cur = db.db["events"].find({"timestamp": {"$gte": start_ts, "$lte": end_ts}})
        first_ref_by_session: Dict[str, str] = {}
        for e in cur:
            sid = e.get("session_id")
            ref = (e.get("properties", {}) or {}).get("referrer") or ""
            if sid and sid not in first_ref_by_session:
                first_ref_by_session[sid] = to_channel(ref)
        cur2 = db.db["events"].find({"event_type": {"$in": ["checkout", "purchase"]}, "timestamp": {"$gte": start_ts, "$lte": end_ts}})
        for e in cur2:
            sid = e.get("session_id")
            ch = to_channel((e.get("properties", {}) or {}).get("referrer") or first_ref_by_session.get(sid, "direct"))
            if e.get("event_type") == "checkout":
                sess_checkout[ch] = sess_checkout.get(ch, 0) + 1
            elif e.get("event_type") == "purchase":
                sess_purchase[ch] = sess_purchase.get(ch, 0) + 1
        for ch in set(list(sess_checkout.keys()) + list(sess_purchase.keys())):
            chk = sess_checkout.get(ch, 0)
            pur = sess_purchase.get(ch, 0)
            abandonment = (1 - (pur / chk)) if chk else None
            # SPA expects fraction (0-1), it multiplies by 100 for display
            channels[ch] = {"abandonment_rate": float(abandonment) if abandonment is not None else None}
    except Exception:
        channels = {}

    # Size distribution by items added per session (very rough)
    size_counter: Dict[str, int] = {"1":0,"2":0,"3":0,"4":0,"5+":0}
    try:
        add_counts: Dict[str, int] = {}
        for e in db.db["events"].find({"event_type": "add_to_cart", "timestamp": {"$gte": start_ts, "$lte": end_ts}}):
            sid = e.get("session_id")
            if not sid:
                continue
            add_counts[sid] = add_counts.get(sid, 0) + int((e.get("properties") or {}).get("quantity", 1) or 1)
        for cnt in add_counts.values():
            if cnt <= 1: size_counter["1"] += 1
            elif cnt == 2: size_counter["2"] += 1
            elif cnt == 3: size_counter["3"] += 1
            elif cnt == 4: size_counter["4"] += 1
            else: size_counter["5+"] += 1
    except Exception:
        pass
    size_distribution = [{"size": k, "count": v} for k, v in size_counter.items()]

    return {
        "metrics": {
            "total_carts": total_carts,
            "active_carts": active_carts,
            "abandoned_carts": abandoned_carts,
            "abandonment_rate": abandonment_rate,
            "avg_items_per_cart": avg_items_per_cart,
            "avg_cart_value": avg_cart_value,
            "total_cart_value": total_cart_value,
        },
        "items": [],
        "abandonment_reasons": [],
        "high_abandonment_categories": [],
        "recommendations": [],
        "recovery_opportunities": [],
        "channels": channels,
        "size_distribution": size_distribution,
    }

async def get_retention_analysis(db, start_date: datetime, cohort_size: int = 7):
    """
    Analyze user retention
    """
    events_col = db.db["events"]
    start_ts = int(start_date.timestamp())
    events = list(events_col.find({
        "timestamp": {"$gte": start_ts}
    }))

    # Safe defaults
    overall_retention_rate = 0.0
    cohort_metrics: list[dict] = []
    retention_periods: list[dict] = []
    user_segments: list[dict] = []
    churn_indicators: list[dict] = []
    engagement_factors: list[dict] = []
    recommendations: list[str] = []
    risk_alerts: list[str] = []

    return {
        "overall_retention_rate": overall_retention_rate,
        "cohort_metrics": cohort_metrics,
        "retention_periods": retention_periods,
        "user_segments": user_segments,
        "churn_indicators": churn_indicators,
        "engagement_factors": engagement_factors,
        "recommendations": recommendations,
        "risk_alerts": risk_alerts,
    }

async def get_seo_analysis(db, start_date: datetime, end_date: datetime):
    """
    Analyze SEO performance
    """
    events_col = db.db["events"]
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    events = list(events_col.find({
        "timestamp": {"$gte": start_ts, "$lte": end_ts}
    }))

    # Safe defaults aligned with SEOAnalysis model
    site_metrics: dict = {
        "total_views": 0,
        "unique_visitors": 0,
        "avg_time_on_site": 0.0,
        "bounce_rate": 0.0,
    }
    top_pages: list[dict] = []
    top_keywords: list[dict] = []
    content_performance: list[dict] = []
    technical_issues: list[dict] = []
    opportunity_keywords: list[dict] = []
    recommendations: list[str] = []
    competitive_gaps: list[dict] = []

    # Build sources.distribution
    def to_channel(ref: str) -> str:
        r = (ref or "").lower()
        if not r or r == "direct":
            return "direct"
        if any(k in r for k in ("google", "bing")):
            return "seo"
        if any(k in r for k in ("facebook", "twitter", "instagram")):
            return "social"
        if "ads" in r:
            return "paid"
        return "referral"

    dist: Dict[str, int] = {"seo":0, "direct":0, "social":0, "referral":0, "paid":0}
    # timeseries: list of {date, seo, direct, social}
    tmap: Dict[str, Dict[str, int]] = {}
    try:
        for e in events:
            if e.get("event_type") not in ("pageview", "search"):
                continue
            ref = (e.get("properties", {}) or {}).get("referrer") or ""
            ch = to_channel(ref)
            dist[ch] = dist.get(ch, 0) + 1
            day = datetime.utcfromtimestamp(int(e.get("timestamp", start_ts))).strftime('%Y-%m-%d')
            bucket = tmap.setdefault(day, {"seo":0, "direct":0, "social":0})
            if ch in ("seo", "direct", "social"):
                bucket[ch] += 1
    except Exception:
        pass

    # Update site metrics basics
    try:
        site_metrics["total_views"] = sum(v.get("seo",0)+v.get("direct",0)+v.get("social",0) for v in tmap.values())
        site_metrics["unique_visitors"] = len(set(e.get("user_id") for e in events if e.get("user_id")))
    except Exception:
        pass

    timeseries = [{"date": d, **vals} for d, vals in sorted(tmap.items())]
    # Build SPA-compatible traffic_trend structure
    categories = [t["date"] for t in timeseries]
    series = [
        {"name": "SEO", "type": "line", "data": [t.get("seo",0) for t in timeseries]},
        {"name": "Direct", "type": "line", "data": [t.get("direct",0) for t in timeseries]},
        {"name": "Social", "type": "line", "data": [t.get("social",0) for t in timeseries]},
    ]

    return {
        "site_metrics": site_metrics,
        "top_pages": top_pages,
        "top_keywords": top_keywords,
        "content_performance": content_performance,
        "technical_issues": technical_issues,
        "opportunity_keywords": opportunity_keywords,
        "recommendations": recommendations,
        "competitive_gaps": competitive_gaps,
        "sources": {"distribution": dist},
        "timeseries": timeseries,
        "traffic_trend": {"categories": categories, "series": series},
    }

async def get_comprehensive_analysis(db, start_date: datetime, end_date: datetime):
    """
    Get comprehensive analytics report
    """
    # Get all analyses in parallel
    journey = await get_user_journey_analysis(db, start_date, end_date)
    cart = await get_cart_analysis(db, start_date, end_date)
    retention = await get_retention_analysis(db, start_date)
    seo = await get_seo_analysis(db, start_date, end_date)
    
    return {
        "journey": journey,
        "cart": cart,
        "retention": retention,
        "seo": seo
    }