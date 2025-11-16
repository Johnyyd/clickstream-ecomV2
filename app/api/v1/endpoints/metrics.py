"""
Metrics endpoints for KPIs and performance tracking
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from app.core.db_sync import events_col, sessions_col, products_col, users_col, carts_col
from app.core.database import db_manager
from app.core.spark import spark_manager
from app.core.cache import cache
from app.core.config import settings
from app.models.user import User
from ..models import (
    BusinessMetrics,
    UserBehaviorMetrics,
    PerformanceMetrics,
    TrendMetrics,
    TimeMetrics
)
from ..deps import get_db, get_current_user, get_optional_user, verify_api_key

router = APIRouter()

@router.get("/business")
async def get_business_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    bypass_cache: bool = False,
    debug: bool = False,
    debug_key: Optional[str] = None,
    db = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get core business metrics (revenue, orders, conversion rates, etc)
    """
    try:
        from app.analytics.metrics import get_business_metrics
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        # Public debug access: allow when debug=true and provided key matches settings.DEBUG_PUBLIC_KEY
        allow_public_debug = False
        try:
            from app.core.config import settings
            allow_public_debug = bool(debug) and debug_key and settings.DEBUG_PUBLIC_KEY and (debug_key == settings.DEBUG_PUBLIC_KEY)
        except Exception:
            allow_public_debug = False

        # Enforce authentication unless public debug is allowed
        if not allow_public_debug and current_user is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authenticated")
            
        key = f"v3:metrics:business:{start_date.isoformat()}:{end_date.isoformat()}:debug={str(bool(debug)).lower()}"
        # When debugging, force bypass to avoid returning cached data without _debug
        effective_bypass = bypass_cache or bool(debug)
        cached = None if effective_bypass else cache.get(key)
        if cached is not None:
            return cached
        result = await get_business_metrics(
            db=db,
            start_date=start_date,
            end_date=end_date,
            debug=bool(debug)
        )
        cache.set(key, result, getattr(settings, 'CACHE_TTL', 3600))
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-behavior")
async def get_user_behavior_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    segment: Optional[str] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user behavior metrics (engagement, sessions, bounce rates, etc)
    """
    try:
        from app.analytics.metrics import get_behavior_metrics
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        key = f"v3:metrics:user_behavior:{start_date.isoformat()}:{end_date.isoformat()}:{segment or 'all'}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = await get_behavior_metrics(
            db=db,
            start_date=start_date,
            end_date=end_date,
            segment=segment
        )
        cache.set(key, result, getattr(settings, 'CACHE_TTL', 3600))
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_performance_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get system performance metrics (success rates, error counts, etc)
    """
    try:
        from app.analytics.metrics import get_performance_metrics
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        key = f"v3:metrics:performance:{start_date.isoformat()}:{end_date.isoformat()}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = await get_performance_metrics(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
        cache.set(key, result, getattr(settings, 'CACHE_TTL', 3600))
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def get_metric_trends(
    metrics: List[str] = Query(..., description="List of metric names to analyze"),
    period: str = "daily",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trend analysis for specified metrics
    """
    try:
        from app.analytics.metrics import get_trends
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        key = f"v3:metrics:trends:{','.join(sorted(metrics or []))}:{period}:{start_date.isoformat()}:{end_date.isoformat()}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = await get_trends(
            db=db,
            metrics=metrics,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        cache.set(key, result, getattr(settings, 'CACHE_TTL', 3600))
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/time-based/{metric_name}")
async def get_time_based_metrics(
    metric_name: str,
    interval: str = "hourly",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get time-based analysis for a specific metric
    """
    try:
        from app.analytics.metrics import get_time_metrics
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
            
        return await get_time_metrics(
            db=db,
            metric_name=metric_name,
            interval=interval,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compare")
async def compare_metrics(
    period1_start: datetime,
    period1_end: datetime,
    period2_start: datetime,
    period2_end: datetime,
    metrics: List[str] = Query(None, description="List of metrics to compare"),
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare metrics between two time periods
    """
    try:
        from app.analytics.metrics import compare_periods
        
        return await compare_periods(
            db=db,
            metrics=metrics,
            period1_start=period1_start,
            period1_end=period1_end,
            period2_start=period2_start,
            period2_end=period2_end
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime")
async def get_realtime_metrics(
    metrics: List[str] = Query(..., description="List of metrics to track in realtime"),
    window_minutes: int = 5,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get real-time metrics with specified window
    """
    try:
        from app.analytics.metrics import get_realtime
        
        return await get_realtime(
            db=db,
            metrics=metrics,
            window_minutes=window_minutes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast/{metric_name}")
async def forecast_metric(
    metric_name: str,
    forecast_days: int = 7,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get forecast for a specific metric
    """
    try:
        from app.analytics.metrics import forecast_metric
        
        return await forecast_metric(
            db=db,
            metric_name=metric_name,
            forecast_days=forecast_days
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))