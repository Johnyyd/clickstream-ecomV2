"""Recommendations analytics module."""
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from app.core.db_sync import events_col


def _events_col(db):  # db kept for backward-compat signature, ignored internally
    return events_col()


def _time_window_bounds(timeframe: Optional[str]) -> Tuple[int, int]:
    now = int(datetime.utcnow().timestamp())
    if timeframe == "hour":
        start = now - 3600
    elif timeframe == "week":
        start = now - 7 * 86400
    elif timeframe == "month":
        start = now - 30 * 86400
    else:  # default day
        start = now - 86400
    return start, now


def _product_key(props: Dict[str, Any]) -> Tuple[str, str, str]:
    pid = str(props.get("product_id") or props.get("sku") or "")
    name = str(props.get("product_name") or props.get("name") or pid)
    cat = str(props.get("category") or props.get("category_name") or "")
    return pid, name, cat


async def get_trending_products(db, timeframe: Optional[str] = "day", category: Optional[str] = None, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
    col = _events_col(db)
    start_ts, end_ts = _time_window_bounds(timeframe)
    match: Dict[str, Any] = {
        "event_type": "purchase",
        "timestamp": {"$gte": start_ts, "$lte": end_ts},
    }
    if category:
        match["properties.category"] = category
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {
                "pid": "$properties.product_id",
                "name": "$properties.product_name",
                "cat": "$properties.category",
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": int(limit or 10)}
    ]
    docs = list(col.aggregate(pipeline))
    recs: List[Dict[str, Any]] = []
    for d in docs:
        pid = (d["_id"] or {}).get("pid") or ""
        name = (d["_id"] or {}).get("name") or pid
        cat = (d["_id"] or {}).get("cat") or ""
        recs.append({
            "product_id": str(pid),
            "product_name": str(name),
            "category": str(cat),
            "confidence_score": 0.5,
            "relevance_score": float(d.get("count", 0)),
            "reason": "Trending purchases",
            "features_matched": [],
            "similar_products": [],
        })
    return recs


async def get_category_recs(db, category: str, user_id: Optional[str] = None, limit: Optional[int] = 10) -> Dict[str, Any]:
    products = await get_trending_products(db, timeframe="week", category=category, limit=limit)
    user_affinity = 0.0
    if user_id:
        # crude affinity: proportion of user's interactions in this category
        col = _events_col(db)
        total = col.count_documents({"user_id": user_id})
        in_cat = col.count_documents({"user_id": user_id, "properties.category": category})
        user_affinity = (in_cat / total) if total else 0.0
    return {
        "category": category,
        "relevance_score": 1.0 if products else 0.0,
        "recommended_products": products,
        "user_affinity": user_affinity,
        "historical_performance": {"purchase_count": sum(int(p.get("relevance_score", 0)) for p in products)},
    }


async def get_similar_products(db, product_id: str, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
    col = _events_col(db)
    # Get category of the given product from last purchase occurrence
    doc = col.find_one(
        {"event_type": "purchase", "properties.product_id": product_id},
        sort=[("timestamp", -1)],
        projection={"properties.category": 1, "properties.product_name": 1}
    )
    category = ((doc or {}).get("properties") or {}).get("category")
    if not category:
        return []
    recs = await get_trending_products(db, timeframe="week", category=category, limit=(limit or 10) + 5)
    # Remove the same product
    filtered = [r for r in recs if r.get("product_id") != product_id]
    return filtered[: int(limit or 10)]


async def get_cross_sell_recs(db, product_id: str, user_id: Optional[str] = None, limit: Optional[int] = 5) -> List[Dict[str, Any]]:
    col = _events_col(db)
    # Find sessions where the product_id was purchased, then other products purchased in same session
    sessions = col.distinct("session_id", {"event_type": "purchase", "properties.product_id": product_id})
    if not sessions:
        return []
    pipeline = [
        {"$match": {"event_type": "purchase", "session_id": {"$in": list(sessions)}}},
        {"$group": {
            "_id": {
                "pid": "$properties.product_id",
                "name": "$properties.product_name",
                "cat": "$properties.category",
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
    ]
    docs = list(col.aggregate(pipeline))
    out: List[Dict[str, Any]] = []
    for d in docs:
        pid = (d["_id"] or {}).get("pid")
        if not pid or str(pid) == str(product_id):
            continue
        name = (d["_id"] or {}).get("name") or pid
        cat = (d["_id"] or {}).get("cat") or ""
        out.append({
            "product_id": str(pid),
            "product_name": str(name),
            "category": str(cat),
            "confidence_score": 0.4,
            "relevance_score": float(d.get("count", 0)),
            "reason": "Frequently bought together",
            "features_matched": [],
            "similar_products": [],
        })
        if len(out) >= int(limit or 5):
            break
    return out


async def get_personalized_recs(db, user_id: Optional[str], limit: Optional[int] = 10, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    uid = user_id or "anonymous"
    col = _events_col(db)
    # User affinity by categories from add_to_cart/checkout/purchase
    match_user = {
        "user_id": uid,
        "event_type": {"$in": ["add_to_cart", "checkout", "purchase"]},
    }
    pipeline = [
        {"$match": match_user},
        {"$group": {"_id": "$properties.category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    cats = list(col.aggregate(pipeline))
    affinity_scores: Dict[str, float] = {}
    total = sum(c.get("count", 0) for c in cats) or 1
    for c in cats:
        cat = c.get("_id") or ""
        affinity_scores[str(cat)] = float(c.get("count", 0)) / total
    preferred_categories = [k for k, _ in sorted(affinity_scores.items(), key=lambda x: x[1], reverse=True)]

    # Recommend trending products from preferred categories
    rec_products: List[Dict[str, Any]] = []
    for cat in preferred_categories:
        if not cat:
            continue
        cat_recs = await get_trending_products(db, timeframe="week", category=cat, limit=limit)
        for r in cat_recs:
            r = dict(r)
            r["confidence_score"] = max(0.5, affinity_scores.get(cat, 0.0))
            r["reason"] = f"Popular in your preferred category: {cat}"
            rec_products.append(r)
        if len(rec_products) >= int(limit or 10):
            break

    # Fallback to global trending if none
    if not rec_products:
        rec_products = await get_trending_products(db, timeframe="week", limit=limit)

    return [{
        "user_id": uid,
        "affinity_scores": affinity_scores,
        "preferred_categories": preferred_categories,
        "recommendations": rec_products[: int(limit or 10)],
        "context": context or {},
    }]


async def get_seasonal_recs(db, season: str, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
    # Simple seasonal proxy: use monthly trending when season is given
    return await get_trending_products(db, timeframe="month", limit=limit)


async def get_complete_recs(db, user_id: Optional[str] = None, product_id: Optional[str] = None, category: Optional[str] = None, limit: Optional[int] = 10) -> Dict[str, Any]:
    return {
        "personalized": await get_personalized_recs(db, user_id=user_id, limit=limit),
        "category_based": [await get_category_recs(db, category or "", user_id=user_id, limit=limit)] if category else [],
        "trending_products": await get_trending_products(db, category=category, limit=limit),
        "similar_products": await get_similar_products(db, product_id or "", limit=limit) if product_id else [],
        "seasonal_recommendations": await get_seasonal_recs(db, season="", limit=limit),
        "cross_sell_suggestions": [],
        "recommendation_metrics": {},
    }