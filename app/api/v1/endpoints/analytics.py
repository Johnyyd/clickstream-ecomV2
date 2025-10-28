"""
Analytics API endpoints
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta

from app.services.analytics import (
    get_user_journey_analysis,
    get_cart_analysis,
    get_retention_analysis,
    get_seo_analysis,
    get_comprehensive_analysis
)
from ..deps import get_db, get_current_user
from ..models import (
    JourneyAnalysis,
    CartAnalysis, 
    RetentionAnalysis,
    SEOAnalysis,
    ComprehensiveAnalysis
)

router = APIRouter()

@router.get("/journey", response_model=JourneyAnalysis)
async def analyze_user_journey(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Analyze user journey patterns
    """
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
        
    return await get_user_journey_analysis(
        db, start_date, end_date, user_id
    )

@router.get("/cart", response_model=CartAnalysis)
async def analyze_cart_behavior(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Analyze shopping cart behavior
    """
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
        
    return await get_cart_analysis(db, start_date, end_date)

@router.get("/retention", response_model=RetentionAnalysis)
async def analyze_user_retention(
    start_date: Optional[datetime] = None,
    cohort_size: Optional[int] = 7,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Analyze user retention rates
    """
    if not start_date:
        start_date = datetime.now() - timedelta(days=90)
        
    return await get_retention_analysis(
        db, start_date, cohort_size
    )

@router.get("/seo", response_model=SEOAnalysis)
async def analyze_seo_performance(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Analyze SEO performance metrics
    """
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
        
    return await get_seo_analysis(db, start_date, end_date)

@router.get("/comprehensive", response_model=ComprehensiveAnalysis)
async def get_comprehensive_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get comprehensive analytics report
    """
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
        
    return await get_comprehensive_analysis(
        db, start_date, end_date
    )