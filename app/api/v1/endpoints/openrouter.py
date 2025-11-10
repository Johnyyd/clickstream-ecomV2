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
        report = await analyze_ml_results(ml_results)
        return {"window": {"start": start_date.isoformat(), "end": end_date.isoformat()}, "report": report}
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