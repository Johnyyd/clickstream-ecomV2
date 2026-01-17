"""
Analytics API endpoints
"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.db_sync import (
    events_col,
    sessions_col,
    products_col,
    users_col,
    carts_col,
)
from app.services.analytics import (
    get_user_journey_analysis,
    get_cart_analysis,
    get_retention_analysis,
    get_seo_analysis,
    get_comprehensive_analysis,
)
from ..deps import get_db, get_current_user

from ..models import (
    JourneyAnalysis,
    CartAnalysis,
    RetentionAnalysis,
    SEOAnalysis,
    ComprehensiveAnalysis,
)

router = APIRouter()

# Simple in-memory orchestration status
_last_orchestration: Dict[str, Any] = {"status": "idle"}
_orchestration_history: list[Dict[str, Any]] = []  # ring buffer of recent runs
_ORCH_HISTORY_MAX = 20

from app.core.cache import cache
from app.core.config import settings
from app.core.database import db_manager


@router.get("/journey")
async def analyze_user_journey(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user_id: Optional[str] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Analyze user journey patterns
    """
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()

    key = f"v3:analytics:journey:{date_from.isoformat()}:{date_to.isoformat()}:{user_id or 'all'}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = await get_user_journey_analysis(db, date_from, date_to, user_id)
    cache.set(key, result, getattr(settings, "CACHE_TTL", 3600))
    return result


@router.get("/cart")
async def analyze_cart_behavior(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Analyze shopping cart behavior
    """
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()

    key = f"v3:analytics:cart:{date_from.isoformat()}:{date_to.isoformat()}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = await get_cart_analysis(db, date_from, date_to)
    cache.set(key, result, getattr(settings, "CACHE_TTL", 3600))
    return result


@router.get("/retention")
async def analyze_user_retention(
    date_from: Optional[datetime] = None,
    cohort_size: Optional[int] = 7,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Analyze user retention rates
    """
    if not date_from:
        date_from = datetime.now() - timedelta(days=90)

    key = f"v3:analytics:retention:{date_from.isoformat()}:{cohort_size}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = await get_retention_analysis(db, date_from, cohort_size)
    cache.set(key, result, getattr(settings, "CACHE_TTL", 3600))
    return result


@router.get("/seo")
async def analyze_seo_performance(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Analyze SEO performance metrics
    """
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()

    key = f"v3:analytics:seo:{date_from.isoformat()}:{date_to.isoformat()}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = await get_seo_analysis(db, date_from, date_to)
    cache.set(key, result, getattr(settings, "CACHE_TTL", 3600))
    return result


@router.get("/comprehensive")
async def get_comprehensive_analytics(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get comprehensive analytics report
    """
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()

    key = f"v3:analytics:comprehensive:{date_from.isoformat()}:{date_to.isoformat()}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = await get_comprehensive_analysis(db, date_from, date_to)
    cache.set(key, result, getattr(settings, "CACHE_TTL", 3600))
    return result


@router.get("/orchestrator/status")
async def get_orchestrator_status(current_user=Depends(get_current_user)):
    """
    Return last orchestration run status and summary
    """
    return _last_orchestration


@router.get("/orchestrator/history")
async def get_orchestrator_history(
    limit: int = Query(10, ge=1, le=50), current_user=Depends(get_current_user)
):
    """
    Return recent orchestration runs (most recent last)
    """
    # Prefer DB; fallback to in-memory buffer
    try:
        col = db_manager.db["orchestrator_runs"]
        docs = list(col.find({}, sort=[("ts", -1)], limit=limit))
        # Clean ObjectId for JSON
        out = []
        for d in docs:
            d.pop("_id", None)
            out.append(d)
        out.reverse()  # most recent last to match previous UI expectation
        return {"items": out}
    except Exception:
        return {"items": _orchestration_history[-limit:]}


@router.get("/orchestrator/history/item")
async def get_orchestrator_history_item(
    ts: str = Query(..., description="Timestamp of the run (ISO string)"),
    current_user=Depends(get_current_user),
):
    """
    Return a single orchestrator run by its timestamp
    """
    # Prefer DB
    try:
        col = db_manager.db["orchestrator_runs"]
        doc = col.find_one({"ts": ts})
        if doc:
            doc.pop("_id", None)
            return doc
    except Exception:
        pass
    # Fallback to memory
    for item in _orchestration_history:
        if item.get("ts") == ts:
            return item
    return {"error": "NOT_FOUND"}


@router.post("/orchestrator/run")
async def run_orchestrator(
    username: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1),
    max_workers: int = Query(4, ge=1, le=16),
    current_user=Depends(get_current_user),
):
    """
    Trigger a comprehensive analytics orchestration run (synchronous)
    """
    try:
        from app.spark.analytics_orchestrator import (
            AnalyticsOrchestrator as SparkOrchestrator,
        )

        orch = SparkOrchestrator()
        result = orch.run_all(username=username, limit=limit, max_workers=max_workers)
        # Normalize minimal status view
        global _last_orchestration
        # Build module summaries if available
        modules_summary: list[dict[str, Any]] = []
        try:
            resmap = result.get("results", {}) or {}
            for name, payload in resmap.items():
                modules_summary.append(
                    {
                        "name": name,
                        "status": (
                            "error"
                            if isinstance(payload, dict) and payload.get("error")
                            else "success"
                        ),
                        "execution_time": (
                            (payload or {}).get("execution_time")
                            if isinstance(payload, dict)
                            else None
                        ),
                    }
                )
        except Exception:
            modules_summary = []
        _last_orchestration = {
            "status": result.get("status", "completed"),
            "start_time": result.get("start_time"),
            "end_time": result.get("end_time"),
            "duration_seconds": result.get("duration_seconds"),
            "module_statistics": result.get("module_statistics"),
            "errors": result.get("errors", {}),
            "username": username,
            "max_workers": max_workers,
            "modules": modules_summary,
        }
        # Append to history (ring buffer)
        item = {"ts": datetime.utcnow().isoformat(), **_last_orchestration}
        # Persist to MongoDB (best-effort)
        try:
            col = db_manager.db["orchestrator_runs"]
            col.insert_one(item)
        except Exception:
            # Fallback to in-memory ring buffer
            _orchestration_history.append(item)
            if len(_orchestration_history) > _ORCH_HISTORY_MAX:
                del _orchestration_history[
                    0 : len(_orchestration_history) - _ORCH_HISTORY_MAX
                ]
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}
