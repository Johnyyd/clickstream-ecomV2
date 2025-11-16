"""
OpenRouter client API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Optional
from datetime import datetime, timedelta

from app.services.openrouter import (
    analyze_user_behavior,
    generate_recommendations,
    get_insights,
    analyze_ml_results
)
from ..deps import get_db, get_current_user, verify_api_key
from app.core.db_sync import api_keys_col
from app.core.db_sync import events_col, sessions_col, products_col, users_col, carts_col
from bson import ObjectId

from ..models import (
    BehaviorAnalysis,
    Recommendations,
    Insights
)

router = APIRouter()

@router.post("/analyze", response_model=BehaviorAnalysis)
async def analyze_behavior(
    user_id: str,
    api_key: str = Depends(verify_api_key),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Analyze user behavior using OpenRouter AI
    """
    try:
        analysis = await analyze_user_behavior(user_id, api_key, db)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report")
async def generate_llm_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate an LLM-powered business report by composing existing analytics
    and passing them to the OpenRouter summarizer. Returns a normalized JSON
    structure suitable for display in the SPA.
    """
    try:
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        from app.analytics.metrics import get_business_metrics
        from app.services.analytics import (
            get_user_journey_analysis,
            get_seo_analysis,
            get_retention_analysis,
        )

        # Collect modules in parallel-ish (sequential await due to simple DB)
        metrics = await get_business_metrics(db=db, start_date=start_date, end_date=end_date)
        journey = await get_user_journey_analysis(db=db, start_date=start_date, end_date=end_date)
        seo = await get_seo_analysis(db=db, start_date=start_date, end_date=end_date)
        # get_retention_analysis signature: (db, start_date: datetime, cohort_size: int = 7)
        retention = await get_retention_analysis(db=db, start_date=start_date)

        ml_results = {
            "business": metrics,
            "journey": journey,
            "seo": seo,
            "retention": retention,
        }

        # Build chart-ready data
        def _num(x):
            try:
                return float(x)
            except Exception:
                return 0.0

        # KPIs
        # Chuẩn hoá lại số session: ưu tiên đếm trực tiếp từ collection sessions
        total_sessions = _num(metrics.get("total_sessions") or metrics.get("sessions") or 0)
        try:
            col_sess = sessions_col()
            # Sử dụng first_event_at trong khoảng window; nếu không có thì fallback last_event_at
            sess_count = col_sess.count_documents({
                "first_event_at": {"$gte": start_date, "$lte": end_date}
            })
            if sess_count == 0:
                sess_count = col_sess.count_documents({
                    "last_event_at": {"$gte": start_date, "$lte": end_date}
                })
            if sess_count:
                total_sessions = float(sess_count)
        except Exception:
            # Nếu có lỗi, giữ nguyên total_sessions từ metrics
            pass

        total_users = _num(metrics.get("total_users") or metrics.get("users") or 0)
        conversion_rate = _num(metrics.get("conversion_rate") or 0)
        revenue = _num(metrics.get("revenue") or 0)
        orders_backend = _num(metrics.get("orders") or 0)

        # Luôn cố gắng suy ra số orders từ funnel (bước Purchase)
        orders_from_funnel = 0.0
        try:
            jf_orders = (journey or {}).get("funnel")
            if isinstance(jf_orders, dict) and isinstance(jf_orders.get("steps"), list):
                steps = jf_orders["steps"]
                purch = next(
                    (
                        s
                        for s in steps
                        if str(s.get("name") or s.get("step") or "").lower().find("purchase") >= 0
                    ),
                    None,
                )
                if purch:
                    orders_from_funnel = _num(purch.get("value") or purch.get("count") or 0)
        except Exception:
            orders_from_funnel = orders_from_funnel or 0.0

        # Tính AOV từ nhiều nguồn, chọn giá trị dương đầu tiên
        aov = 0.0
        aov_candidates = [
            _num(metrics.get("average_order_value") or 0),
            _num(metrics.get("aov") or 0),
        ]
        if revenue > 0 and orders_backend > 0:
            try:
                aov_candidates.append(revenue / orders_backend)
            except Exception:
                pass
        if revenue > 0 and orders_from_funnel > 0:
            try:
                aov_candidates.append(revenue / orders_from_funnel)
            except Exception:
                pass
        for cand in aov_candidates:
            if cand and cand > 0:
                aov = cand
                break
        if total_sessions <= 0:
            tv = _num(((seo or {}).get("site_metrics") or {}).get("total_views") or 0)
            if tv > 0:
                total_sessions = tv
        if conversion_rate <= 0:
            jf = (journey or {}).get("funnel")
            try:
                if isinstance(jf, dict) and "steps" in jf and isinstance(jf["steps"], list):
                    steps = jf["steps"]
                    views = next((s for s in steps if str(s.get("name") or s.get("step") or "").lower().find("view") >= 0), None)
                    purch = next((s for s in steps if str(s.get("name") or s.get("step") or "").lower().find("purchase") >= 0), None)
                    v = _num((views or {}).get("value") or (views or {}).get("count") or 0)
                    p = _num((purch or {}).get("value") or (purch or {}).get("count") or 0)
                    conversion_rate = (p / v) if v > 0 else 0
                elif isinstance(jf, dict):
                    v = _num(jf.get("Views") or jf.get("views") or jf.get("view") or 0)
                    p = _num(jf.get("Purchase") or jf.get("purchase") or 0)
                    conversion_rate = (p / v) if v > 0 else 0
            except Exception:
                pass

        # Funnel
        funnel = []
        jf = (journey or {}).get("funnel")
        if jf:
            if isinstance(jf, dict) and isinstance(jf.get("steps"), list):
                for s in jf["steps"]:
                    name = s.get("name") or s.get("step") or ""
                    val = _num(s.get("value") or s.get("count") or 0)
                    if name:
                        funnel.append({"name": name, "value": val})
            elif isinstance(jf, dict):
                for k, v in jf.items():
                    funnel.append({"name": str(k), "value": _num(v)})

        # Nếu AOV vẫn chưa dương nhưng funnel local đã có bước Purchase, dùng funnel để tính lại
        if (not aov or aov <= 0) and revenue > 0 and funnel:
            try:
                purch_step = next(
                    (
                        s
                        for s in funnel
                        if str(s.get("name") or "").lower().find("purchase") >= 0
                    ),
                    None,
                )
                if purch_step:
                    purch_cnt = _num(purch_step.get("value") or 0)
                    if purch_cnt > 0:
                        aov = revenue / purch_cnt
            except Exception:
                pass

        # Bước cuối: tính trực tiếp AOV từ collection events để đảm bảo khớp dữ liệu Mongo
        # Dựa trên schema event purchase: properties.total_amount, hoặc price * cart_items
        if not aov or aov <= 0:
            try:
                col_events = events_col()
                # Window theo timestamp epoch seconds
                start_ts_ev = int(start_date.timestamp())
                end_ts_ev = int(end_date.timestamp())
                purchase_match_ev = {
                    "$and": [
                        {
                            "$or": [
                                {"event_type": "purchase"},
                                {
                                    "$expr": {
                                        "$eq": [
                                            {"$toLower": {"$trim": {"input": "$event_type"}}},
                                            "purchase",
                                        ]
                                    }
                                },
                            ]
                        },
                        {
                            "timestamp": {
                                "$gte": start_ts_ev,
                                "$lte": end_ts_ev,
                            }
                        },
                    ]
                }

                docs = list(
                    col_events.find(
                        purchase_match_ev,
                        {
                            "properties.total_amount": 1,
                            "properties.total": 1,
                            "properties.amount": 1,
                            "properties.value": 1,
                            "properties.cart_total": 1,
                            "properties.product_details.price": 1,
                            "properties.cart_items": 1,
                        },
                    )
                )

                def _to_float_ev(x) -> float:
                    try:
                        return float(x)
                    except Exception:
                        try:
                            return float(str(x).replace(",", ""))
                        except Exception:
                            return 0.0

                def _to_amount_ev(doc) -> float:
                    props = (doc.get("properties") or {})
                    for k in ("total_amount", "total", "amount", "value", "cart_total"):
                        if k in props and props.get(k) not in (None, ""):
                            return _to_float_ev(props.get(k))
                    price = None
                    try:
                        pd = props.get("product_details") or {}
                        if isinstance(pd, dict):
                            price = pd.get("price")
                    except Exception:
                        price = None
                    items = props.get("cart_items") or 1
                    price_f = _to_float_ev(price) if price is not None else 0.0
                    items_f = _to_float_ev(items) if items is not None else 1.0
                    return price_f * items_f

                orders_ev = len(docs)
                revenue_ev = sum(_to_amount_ev(d) for d in docs)
                if revenue_ev > 0 and orders_ev > 0:
                    aov = revenue_ev / orders_ev
            except Exception:
                # Nếu có lỗi truy vấn trực tiếp events, giữ nguyên aov hiện tại
                pass

        # Top paths
        links = []
        jp = (journey or {}).get("paths")
        if isinstance(jp, dict) and isinstance(jp.get("links"), list):
            links = jp["links"]
        elif isinstance(jp, list):
            links = jp
        elif isinstance((journey or {}).get("top_paths"), list):
            links = journey.get("top_paths")
        if isinstance(links, list):
            links = sorted(links, key=lambda x: _num((x or {}).get("value") or 0), reverse=True)[:100]

        # SEO distribution
        seo_distribution = []
        try:
            dist = ((seo or {}).get("sources") or {}).get("distribution") or {}
            if isinstance(dist, dict):
                seo_distribution = [{"name": str(k), "value": _num(v)} for k, v in dist.items()]
        except Exception:
            pass

        # Retention timeseries
        retention_ts = []
        try:
            ts = (retention or {}).get("timeseries")
            if isinstance(ts, list):
                for r in ts:
                    retention_ts.append({
                        "date": str(r.get("date") or r.get("time") or r.get("t") or ""),
                        "retained": _num(r.get("retained") or 0),
                        "churned": _num(r.get("churned") or 0),
                    })
        except Exception:
            pass

        # Data quality
        dq = {}
        try:
            dq_src = metrics.get("data_quality") if isinstance(metrics, dict) else None

            events_count = 0.0
            last_event_ts = None
            col = events_col()

            try:
                start_ts = int(start_date.timestamp())
                end_ts = int(end_date.timestamp())
                time_filter = {"timestamp": {"$gte": start_ts, "$lte": end_ts}}

                events_count = float(col.count_documents(time_filter))

                doc_last_cur = col.find(
                    time_filter,
                    {"timestamp": 1, "occurred_at": 1, "occurred_at_iso": 1},
                ).sort([("timestamp", -1)]).limit(1)
                docs = list(doc_last_cur)
                if docs:
                    d = docs[0]
                    if d.get("occurred_at") is not None:
                        try:
                            last_event_ts = d["occurred_at"].isoformat()
                        except Exception:
                            last_event_ts = str(d["occurred_at"])
                    elif d.get("occurred_at_iso"):
                        last_event_ts = str(d["occurred_at_iso"])
                    elif d.get("timestamp") is not None:
                        import datetime as _dt
                        ts = int(d["timestamp"])
                        last_event_ts = _dt.datetime.utcfromtimestamp(ts).isoformat()
            except Exception:
                pass

            sessions_count = total_sessions
            dq = {
                "events_count": events_count,
                "sessions_count": sessions_count,
                "missing_values_pct": _num((dq_src or {}).get("missing_values_pct") or 0),
                "duplicate_events_pct": _num((dq_src or {}).get("duplicate_events_pct") or 0),
                "last_event_ts": last_event_ts,
            }
        except Exception:
            dq = {"events_count": 0, "sessions_count": total_sessions, "missing_values_pct": 0, "duplicate_events_pct": 0, "last_event_ts": None}

        # Fallback revenue from SEO when business revenue is zero
        if revenue <= 0:
            try:
                seo_rev = _num((seo or {}).get("revenue") or 0)
                if seo_rev > 0:
                    revenue = seo_rev
            except Exception:
                pass

        charts = {
            "kpis": {
                "sessions": total_sessions,
                "users": total_users,
                "cr": conversion_rate,
                "revenue": revenue,
                "aov": aov,
            },
            "funnel": funnel,
            "top_paths": links,
            "seo_distribution": seo_distribution,
            "retention_timeseries": retention_ts,
            "data_quality": dq,
        }

        # Đồng bộ lại ml_results.business cho LLM: đảm bảo thấy đúng KPI & data_quality backend
        try:
            biz = dict(metrics or {}) if isinstance(metrics, dict) else {}
            biz["total_sessions"] = total_sessions
            biz["sessions"] = total_sessions
            biz["total_users"] = total_users
            biz["users"] = total_users
            biz["conversion_rate"] = conversion_rate
            biz["revenue"] = revenue
            biz["average_order_value"] = aov
            biz["aov"] = aov
            biz["data_quality"] = dq
            ml_results["business"] = biz
        except Exception:
            ml_results["business"] = metrics

        # Resolve OpenRouter API key: ưu tiên key lưu trong Mongo cho admin, fallback sang settings
        api_key_override = None
        try:
            role = getattr(current_user, "role", None)
            if not role and isinstance(current_user, dict):
                role = current_user.get("role")
            if role == "admin":
                # Lấy user_id theo nhiều dạng (model hoặc dict)
                uid = None
                for attr in ("id", "_id"):
                    if hasattr(current_user, attr):
                        uid = getattr(current_user, attr)
                        if uid is not None:
                            break
                if uid is None and isinstance(current_user, dict):
                    uid = current_user.get("_id")
                if uid is not None:
                    # user_id trong collection api_keys được lưu dạng ObjectId
                    query_uid = uid
                    try:
                        if isinstance(query_uid, str):
                            query_uid = ObjectId(query_uid)
                    except Exception:
                        # Nếu không convert được thì vẫn thử với giá trị gốc
                        query_uid = uid

                    doc = api_keys_col().find_one({"user_id": query_uid, "provider": "openrouter"})
                    if doc:
                        # Hỗ trợ cả schema mới (key_encrypted) lẫn cũ (key)
                        key_val = doc.get("key_encrypted") or doc.get("key")
                        if key_val:
                            api_key_override = key_val
        except Exception:
            api_key_override = None

        report = await analyze_ml_results(ml_results, api_key=api_key_override)

        # Đảm bảo phần data_quality trong parsed.charts luôn dùng số liệu backend (dq)
        if isinstance(report, dict):
            parsed = report.get("parsed") or {}
            charts_parsed = parsed.get("charts") or {}
            charts_parsed["data_quality"] = dq
            parsed["charts"] = charts_parsed
            # Đồng bộ KPIs trong parsed.kpis theo backend charts.kpis (bao gồm aov)
            kpis_backend = charts.get("kpis") or {}
            # Giữ lại các field khác của LLM nếu có nhưng ghi đè 4 KPI chính và aov
            kpis_llm = parsed.get("kpis") or {}
            kpis_llm.update({
                "sessions": kpis_backend.get("sessions"),
                "users": kpis_backend.get("users"),
                "cr": kpis_backend.get("cr"),
                "revenue": kpis_backend.get("revenue"),
                "aov": kpis_backend.get("aov"),
            })
            parsed["kpis"] = kpis_llm
            report["parsed"] = parsed

        # Attach meta for troubleshooting source of LLM (openrouter|fallback)
        meta = {"llm_source": report.get("source")} if isinstance(report, dict) else {}
        # Fallback for users: if zero, try SEO unique_visitors
        if charts["kpis"]["users"] <= 0:
            uv = _num(((seo or {}).get("site_metrics") or {}).get("unique_visitors") or 0)
            if uv > 0:
                charts["kpis"]["users"] = uv
        return {"window": {"start": start_date.isoformat(), "end": end_date.isoformat()}, "report": report, "charts": charts, "meta": meta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommend", response_model=Recommendations)
async def get_recommendations(
    user_id: str,
    api_key: str = Depends(verify_api_key),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get AI-powered recommendations
    """
    try:
        recs = await generate_recommendations(user_id, api_key, db)
        return recs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/insights", response_model=Insights)
async def get_behavior_insights(
    user_id: str,
    api_key: str = Depends(verify_api_key),
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get AI-generated behavior insights
    """
    try:
        insights = await get_insights(user_id, api_key, db)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))