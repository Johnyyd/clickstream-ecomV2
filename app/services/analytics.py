"""
Analytics service functions
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.core.db_sync import events_col

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

    col = events_col()
    events = list(col.find(query))

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

    # Build Top Paths (Sankey) from per-session sequences
    paths_nodes: set[str] = set()
    paths_counter: dict[tuple[str, str], int] = {}
    try:
        # Group events by session and sort by timestamp
        by_session: dict[str, list[dict]] = {}
        for e in events:
            sid = e.get("session_id")
            if not sid:
                continue
            by_session.setdefault(sid, []).append(e)

        def label_for(e: dict) -> str:
            et = (e.get("event_type") or "").lower()
            props = (e.get("properties") or {})
            # Prefer human friendly page labels
            page = props.get("page") or props.get("title") or props.get("name")
            if et in ("pageview", "search") or ("view" in et):
                return str(page or props.get("path") or "Page")
            if et == "add_to_cart":
                return "Add to Cart"
            if et == "checkout":
                return "Checkout"
            if et == "purchase":
                return "Purchase"
            # fallback to event_type
            return et.title() or "Event"

        # Define a stage order to keep graph acyclic
        STAGE_ORDER = {
            "Views": 0, "View": 0, "Page": 0,
            "Add to Cart": 1,
            "Checkout": 2,
            "Purchase": 3,
        }
        def stage_of(label: str) -> int:
            # Unknown labels default to 0 (treated as early-stage pages)
            return STAGE_ORDER.get(label, 0)

        for sid, evs in by_session.items():
            evs.sort(key=lambda x: int(x.get("timestamp", 0)))
            # Build sequence of labels; collapse duplicates in a row
            seq: list[str] = []
            last = None
            for e in evs:
                lbl = label_for(e)
                if not lbl:
                    continue
                if lbl != last:
                    seq.append(lbl)
                    last = lbl
            # Count adjacent transitions (forward only) and avoid in-session duplicates
            seen_edges_in_session: set[tuple[str,str]] = set()
            for i in range(len(seq)-1):
                a, b = seq[i], seq[i+1]
                if not a or not b or a == b:
                    continue
                # Keep only strictly forward transitions to avoid cycles (drop same-stage and backward)
                if stage_of(a) >= stage_of(b):
                    continue
                edge = (a, b)
                if edge in seen_edges_in_session:
                    continue
                seen_edges_in_session.add(edge)
                paths_nodes.add(a); paths_nodes.add(b)
                paths_counter[edge] = paths_counter.get(edge, 0) + 1

        # Build nodes/links for Sankey, keep top N links
        topN = 40
        links = sorted(({"source": a, "target": b, "value": c} for (a, b), c in paths_counter.items()), key=lambda x: x["value"], reverse=True)[:topN]
        nodes = sorted({n for n in paths_nodes})
        # Provide both compact top_paths (for any consumer) and SPA-compatible 'paths'
        top_paths = links
        paths = {"nodes": nodes, "links": links}
    except Exception:
        paths = None

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
        # SPA expects paths to have {nodes, links}
        "paths": paths,
    }

async def get_cart_analysis(db, start_date: datetime, end_date: datetime):
    """
    Analyze cart behavior
    """
    col = events_col()
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    cart_events = list(col.find({
        "event_type": {"$in": ["add_to_cart", "remove_from_cart", "checkout"]},
        "timestamp": {"$gte": start_ts, "$lte": end_ts}
    }))
    
    # Process cart data (safe defaults)
    total_carts = 0
    active_carts = 0
    abandoned_carts = 0
    total_cart_value = 0.0
    avg_items_per_cart = 0.0
    avg_cart_value = 0.0
    abandonment_rate = 0.0

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
        cur = col.find({"timestamp": {"$gte": start_ts, "$lte": end_ts}})
        first_ref_by_session: Dict[str, str] = {}
        for e in cur:
            sid = e.get("session_id")
            ref = (e.get("properties", {}) or {}).get("referrer") or ""
            if sid and sid not in first_ref_by_session:
                first_ref_by_session[sid] = to_channel(ref)
        cur2 = col.find({"event_type": {"$in": ["checkout", "purchase"]}, "timestamp": {"$gte": start_ts, "$lte": end_ts}})
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
        for e in col.find({"event_type": "add_to_cart", "timestamp": {"$gte": start_ts, "$lte": end_ts}}):
            sid = e.get("session_id")
            if not sid:
                continue
            qty = int((e.get("properties") or {}).get("quantity", 1) or 1)
            add_counts[sid] = add_counts.get(sid, 0) + qty

        # Derive total_carts and avg_items_per_cart from add_counts
        total_carts = len(add_counts)
        if total_carts > 0:
            total_items = sum(add_counts.values())
            avg_items_per_cart = total_items / float(total_carts)

        # Mark size buckets
        for cnt in add_counts.values():
            if cnt <= 1: size_counter["1"] += 1
            elif cnt == 2: size_counter["2"] += 1
            elif cnt == 3: size_counter["3"] += 1
            elif cnt == 4: size_counter["4"] += 1
            else: size_counter["5+"] += 1

        # Derive abandoned_carts and abandonment_rate from sessions with add_to_cart but no purchase
        try:
            purchase_sids: Dict[str, int] = {}
            for e in col.find({"event_type": "purchase", "timestamp": {"$gte": start_ts, "$lte": end_ts}}):
                sid = e.get("session_id")
                if not sid:
                    continue
                purchase_sids[sid] = purchase_sids.get(sid, 0) + 1
            abandoned_carts = len([sid for sid in add_counts.keys() if sid not in purchase_sids])
            abandonment_rate = (abandoned_carts / float(total_carts)) if total_carts > 0 else 0.0
        except Exception:
            abandoned_carts = abandoned_carts or 0
            abandonment_rate = abandonment_rate or 0.0
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
    col = events_col()
    start_ts = int(start_date.timestamp())
    events = list(col.find({
        "timestamp": {"$gte": start_ts}
    }, {"user_id":1, "timestamp":1}))

    # Defaults
    timeseries: list[dict] = []
    cohort: list[dict] = []
    try:
        # Build month buckets
        from datetime import datetime as _dt
        def month_key(ts: int) -> str:
            return _dt.utcfromtimestamp(int(ts)).strftime('%Y-%m')

        # Map: user_id -> set of active months
        user_months: dict[str, set[str]] = {}
        for e in events:
            uid = e.get("user_id")
            if not uid:
                continue
            mk = month_key(e.get("timestamp", start_ts))
            user_months.setdefault(str(uid), set()).add(mk)

        # Build contiguous month list from min to max month seen
        if user_months:
            all_months = sorted({m for s in user_months.values() for m in s})
        else:
            all_months = []
        def to_ym(mstr: str):
            y, m = map(int, mstr.split('-'))
            return y, m
        def ym_iter(start_m: str, end_m: str):
            sy, sm = to_ym(start_m)
            ey, em = to_ym(end_m)
            y, m = sy, sm
            out = []
            while (y < ey) or (y == ey and m <= em):
                out.append(f"{y:04d}-{m:02d}")
                m += 1
                if m > 12:
                    m = 1; y += 1
            return out
        months_sorted = ym_iter(all_months[0], all_months[-1]) if all_months else []

        # Active users per month as sets
        active_sets: dict[str, set[str]] = {m: set() for m in months_sorted}
        for uid, months in user_months.items():
            for m in months:
                if m in active_sets:
                    active_sets[m].add(uid)

        # Timeseries retention = returning users (consecutive months) / active users in previous month
        prev_m = None
        for m in months_sorted:
            if prev_m is None:
                timeseries.append({"date": m, "retention": 0.0, "churn": 0.0})
            else:
                prev_users = active_sets.get(prev_m, set())
                cur_users = active_sets.get(m, set())
                if prev_users:
                    returning = len(prev_users & cur_users)
                    retention = round(returning / len(prev_users), 4)
                else:
                    retention = 0.0
                churn = max(0.0, 1.0 - retention)
                timeseries.append({"date": m, "retention": retention, "churn": churn})
            prev_m = m

        # Build cohorts: group by first month seen
        cohorts: dict[str, list[str]] = {}
        for uid, months in user_months.items():
            if not months:
                continue
            fm = sorted(months)[0]
            cohorts.setdefault(fm, []).append(uid)

        # For each cohort, compute retention across next 5 months
        from datetime import datetime as _dt
        def next_months(start_m: str, n: int = 5) -> list[str]:
            # start_m format 'YYYY-MM'
            y, m = map(int, start_m.split('-'))
            arr = []
            yy, mm = y, m
            for _ in range(n):
                arr.append(f"{yy:04d}-{mm:02d}")
                mm += 1
                if mm > 12:
                    mm = 1
                    yy += 1
            return arr

        for cm, users in sorted(cohorts.items()):
            size = len(users)
            horizon = next_months(cm, 6)  # include cohort month
            months_ret = []
            user_set = set(users)
            for m in horizon:
                # retained if user has activity in month m
                active = 0
                for uid in user_set:
                    if m in user_months.get(uid, set()):
                        active += 1
                months_ret.append(round((active/size) if size else 0.0, 4))
            cohort.append({"cohort": cm, "size": size, "months": months_ret})
    except Exception:
        # ignore errors and keep defaults
        pass

    return {
        "timeseries": timeseries,
        "cohort": cohort,
    }

async def get_seo_analysis(db, start_date: datetime, end_date: datetime):
    """
    Analyze SEO performance
    """
    col = events_col()
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    events = list(col.find({
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

    # Pull revenue from business metrics to expose in this API as requested
    revenue_value: float = 0.0
    try:
        from app.analytics.metrics import get_business_metrics as _get_biz
        biz = await _get_biz(db=db, start_date=start_date, end_date=end_date)
        revenue_value = float(biz.get("revenue", 0.0) or 0.0)
    except Exception:
        revenue_value = 0.0

    # If revenue still 0, run an internal aggregation directly on events as a fallback
    if not revenue_value:
        try:
            col = events_col()
            # Normalize window bounds
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())
            pipeline = [
                {"$match": {"$and": [
                    {"$or": [
                        {"event_type": "purchase"},
                        {"$expr": {"$eq": [ {"$toLower": {"$trim": {"input": "$event_type"}}}, "purchase" ]}}
                    ]},
                    {"$or": [
                        {"timestamp": {"$gte": start_ts, "$lte": end_ts}},
                        {"timestamp": {"$gte": start_ts * 1000, "$lte": end_ts * 1000}},
                        {"occurred_at": {"$gte": start_date, "$lte": end_date}},
                        {"$expr": {"$and": [
                            {"$gte": [ {"$toLong": "$timestamp"}, start_ts ]},
                            {"$lte": [ {"$toLong": "$timestamp"}, end_ts ]}
                        ]}},
                        {"$expr": {"$and": [
                            {"$gte": [ {"$toLong": "$timestamp"}, start_ts * 1000 ]},
                            {"$lte": [ {"$toLong": "$timestamp"}, end_ts * 1000 ]}
                        ]}},
                        {"$expr": {"$and": [
                            {"$gte": [ {"$dateFromString": {"dateString": "$occurred_at_iso", "onError": None, "onNull": None}}, start_date ]},
                            {"$lte": [ {"$dateFromString": {"dateString": "$occurred_at_iso", "onError": None, "onNull": None}}, end_date ]}
                        ]}}
                    ]}
                ]}},
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
                {"$group": {"_id": None, "rev": {"$sum": "$final"}}}
            ]
            agg = list(col.aggregate(pipeline))
            if agg:
                revenue_value = float(agg[0].get("rev") or 0.0)
        except Exception:
            pass

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
        "revenue": revenue_value,
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