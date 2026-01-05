"""
Analyses endpoints for different types of analytics
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from app.core.db_sync import (
    events_col,
    sessions_col,
    products_col,
    users_col,
    carts_col,
)
from app.core.database import db_manager
from app.core.spark import spark_manager
from app.models.user import User
from ..models import (
    JourneyAnalysis,
    CartAnalysis,
    RetentionAnalysis,
    SEOAnalysis,
    BehaviorAnalysis,
    Recommendations,
    Insights,
    ComprehensiveAnalysis,
)
from ..deps import get_db, get_current_user, verify_api_key

router = APIRouter()


@router.get("/journey", response_model=JourneyAnalysis)
async def analyze_user_journey(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze user journey patterns and paths
    """
    try:
        from app.analytics.journey import analyze_journey

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        return await analyze_journey(
            db=db, start_date=start_date, end_date=end_date, user_id=user_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cart", response_model=CartAnalysis)
async def analyze_cart_behavior(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze shopping cart behavior and abandonment
    """
    try:
        from app.analytics.cart import analyze_cart

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        return await analyze_cart(db=db, start_date=start_date, end_date=end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retention", response_model=RetentionAnalysis)
async def analyze_user_retention(
    start_date: Optional[datetime] = None,
    cohort_size: Optional[int] = 7,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze user retention and cohort behavior
    """
    try:
        from app.analytics.retention import analyze_retention

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=90)

        return await analyze_retention(
            db=db, start_date=start_date, cohort_size=cohort_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/seo", response_model=SEOAnalysis)
async def analyze_seo_performance(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze SEO and traffic performance metrics
    """
    try:
        from app.analytics.seo import analyze_seo

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        return await analyze_seo(db=db, start_date=start_date, end_date=end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/behavior", response_model=BehaviorAnalysis)
async def analyze_user_behavior(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze detailed user behavior patterns
    """
    try:
        from app.analytics.behavior import analyze_behavior

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        return await analyze_behavior(
            db=db, start_date=start_date, end_date=end_date, user_id=user_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations", response_model=Recommendations)
async def get_recommendations(
    user_id: Optional[str] = None,
    product_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = 10,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get personalized product recommendations
    """
    try:
        from app.analytics.recommendations import generate_recommendations

        return await generate_recommendations(
            db=db,
            user_id=user_id,
            product_id=product_id,
            category=category,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", response_model=Insights)
async def get_business_insights(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metrics: Optional[List[str]] = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get AI-powered business insights and recommendations
    """
    try:
        from app.analytics.insights import generate_insights

        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        return await generate_insights(
            db=db, start_date=start_date, end_date=end_date, metrics=metrics
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
