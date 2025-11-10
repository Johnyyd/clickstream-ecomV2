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
        total_sessions = _num(metrics.get("total_sessions") or metrics.get("sessions") or 0)
        total_users = _num(metrics.get("total_users") or metrics.get("users") or 0)
        conversion_rate = _num(metrics.get("conversion_rate") or 0)
        revenue = _num(metrics.get("revenue") or 0)
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
            events_count = _num(metrics.get("total_events") or 0)
            sessions_count = total_sessions
            dq = {
                "events_count": events_count,
                "sessions_count": sessions_count,
                "missing_values_pct": _num((dq_src or {}).get("missing_values_pct") or 0),
                "duplicate_events_pct": _num((dq_src or {}).get("duplicate_events_pct") or 0),
                "last_event_ts": (metrics.get("last_event_ts") if isinstance(metrics, dict) else None),
            }
        except Exception:
            dq = {"events_count": 0, "sessions_count": total_sessions, "missing_values_pct": 0, "duplicate_events_pct": 0, "last_event_ts": None}

        charts = {
            "kpis": {
                "sessions": total_sessions,
                "users": total_users,
                "cr": conversion_rate,
                "revenue": revenue,
            },
            "funnel": funnel,
            "top_paths": links,
            "seo_distribution": seo_distribution,
            "retention_timeseries": retention_ts,
            "data_quality": dq,
        }

        report = await analyze_ml_results(ml_results)
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