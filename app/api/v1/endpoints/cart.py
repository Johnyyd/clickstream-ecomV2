"""
Cart endpoints for cart management and analysis
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from app.core.db_sync import events_col, sessions_col, products_col, users_col, carts_col
from app.core.database import db_manager
from app.core.spark import spark_manager
from app.models.user import User
from ..models import (
    CartItem,
    CartMetrics,
    CartAbandonmentReason,
    CartAnalysis
)
from ..deps import get_db, get_current_user, verify_api_key

router = APIRouter()

@router.get("/active", response_model=List[CartItem])
async def get_active_carts(
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of currently active shopping carts
    """
    try:
        from app.services.cart import get_active_carts
        
        return await get_active_carts(
            db=db,
            limit=limit,
            skip=skip
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/abandoned", response_model=List[CartItem])
async def get_abandoned_carts(
    days: Optional[int] = 7,
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of abandoned shopping carts
    """
    try:
        from app.services.cart import get_abandoned_carts
        
        return await get_abandoned_carts(
            db=db,
            days=days,
            limit=limit,
            skip=skip
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", response_model=CartMetrics)
async def get_cart_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cart-related metrics and KPIs
    """
    try:
        from app.services.cart import get_cart_metrics
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        return await get_cart_metrics(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/abandonment/reasons", response_model=List[CartAbandonmentReason])
async def get_abandonment_reasons(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get analysis of cart abandonment reasons
    """
    try:
        from app.services.cart import get_abandonment_reasons
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        return await get_abandonment_reasons(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis", response_model=CartAnalysis)
async def get_cart_analysis(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive cart analysis including metrics, patterns, and recommendations
    """
    try:
        from app.services.cart import get_cart_analysis
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        return await get_cart_analysis(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}", response_model=List[CartItem])
async def get_user_cart_history(
    user_id: str,
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cart history for a specific user
    """
    try:
        from app.services.cart import get_user_cart_history
        
        return await get_user_cart_history(
            db=db,
            user_id=user_id,
            limit=limit,
            skip=skip
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recovery/suggestions", response_model=Dict[str, Any])
async def get_cart_recovery_suggestions(
    cart_id: str,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get personalized suggestions for cart recovery
    """
    try:
        from app.services.cart import get_recovery_suggestions
        
        return await get_recovery_suggestions(
            db=db,
            cart_id=cart_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recovery/campaign", response_model=Dict[str, Any])
async def create_recovery_campaign(
    cart_ids: List[str],
    campaign_type: str = "email",
    template_id: Optional[str] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a cart recovery campaign for abandoned carts
    """
    try:
        from app.services.cart import create_recovery_campaign
        
        return await create_recovery_campaign(
            db=db,
            cart_ids=cart_ids,
            campaign_type=campaign_type,
            template_id=template_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends", response_model=Dict[str, Any])
async def get_cart_trends(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metrics: List[str] = Query(None),
    interval: str = "daily",
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trend analysis for cart-related metrics
    """
    try:
        from app.services.cart import get_cart_trends
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        return await get_cart_trends(
            db=db,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            interval=interval
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))