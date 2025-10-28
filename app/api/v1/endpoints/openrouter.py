"""
OpenRouter client API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Optional

from app.services.openrouter import (
    analyze_user_behavior,
    generate_recommendations,
    get_insights
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