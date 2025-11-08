"""
Recommendation endpoints for product suggestions
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from app.core.database import db_manager
from app.core.spark import spark_manager
from app.models.user import User
from ..models import (
    Recommendations,
    ProductRecommendation,
    CategoryRecommendation,
    PersonalizedRecommendation
)
from ..deps import get_db, get_current_user, verify_api_key

router = APIRouter()

@router.get("/personalized", response_model=List[PersonalizedRecommendation])
async def get_personalized_recommendations(
    user_id: Optional[str] = None,
    limit: Optional[int] = 10,
    context: Optional[Dict[str, Any]] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get personalized product recommendations for a user
    """
    try:
        from app.analytics.recommendations import get_personalized_recs
        if not user_id and current_user:
            user_id = str(getattr(current_user, "id", "") or "")
        result = await get_personalized_recs(
            db=db,
            user_id=user_id,
            limit=limit,
            context=context
        )
        # Ensure list shape
        if not isinstance(result, list):
            result = []
        return result
    except Exception:
        # Fail-safe: return empty list for UI to render empty state
        return []

@router.get("/similar-products/{product_id}", response_model=List[ProductRecommendation])
async def get_similar_products(
    product_id: str,
    limit: Optional[int] = 10,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get similar product recommendations based on a product
    """
    try:
        from app.analytics.recommendations import get_similar_products
        
        return await get_similar_products(
            db=db,
            product_id=product_id,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/category/{category}", response_model=CategoryRecommendation)
async def get_category_recommendations(
    category: str,
    user_id: Optional[str] = None,
    limit: Optional[int] = 10,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recommendations for products in a specific category
    """
    try:
        from app.analytics.recommendations import get_category_recs
        
        if not user_id and current_user:
            user_id = str(current_user.id)
            
        return await get_category_recs(
            db=db,
            category=category,
            user_id=user_id,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending", response_model=List[ProductRecommendation])
async def get_trending_products(
    timeframe: Optional[str] = "day",
    category: Optional[str] = None,
    limit: Optional[int] = 10,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get currently trending products
    """
    try:
        from app.analytics.recommendations import get_trending_products
        
        return await get_trending_products(
            db=db,
            timeframe=timeframe,
            category=category,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/seasonal", response_model=List[ProductRecommendation])
async def get_seasonal_recommendations(
    season: Optional[str] = None,
    limit: Optional[int] = 10,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get seasonal product recommendations
    """
    try:
        from app.analytics.recommendations import get_seasonal_recs
        
        # If no season specified, use current season
        if not season:
            current_month = datetime.utcnow().month
            if 3 <= current_month <= 5:
                season = "spring"
            elif 6 <= current_month <= 8:
                season = "summer"
            elif 9 <= current_month <= 11:
                season = "fall"
            else:
                season = "winter"
                
        return await get_seasonal_recs(
            db=db,
            season=season,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cross-sell/{product_id}", response_model=List[ProductRecommendation])
async def get_cross_sell_recommendations(
    product_id: str,
    user_id: Optional[str] = None,
    limit: Optional[int] = 5,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cross-sell product recommendations
    """
    try:
        from app.analytics.recommendations import get_cross_sell_recs
        
        if not user_id and current_user:
            user_id = str(current_user.id)
            
        return await get_cross_sell_recs(
            db=db,
            product_id=product_id,
            user_id=user_id,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/complete", response_model=Recommendations)
async def get_all_recommendations(
    user_id: Optional[str] = None,
    product_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = 10,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete set of recommendations including personalized, similar, trending, and seasonal
    """
    try:
        from app.analytics.recommendations import get_complete_recs
        
        if not user_id and current_user:
            user_id = str(current_user.id)
            
        return await get_complete_recs(
            db=db,
            user_id=user_id,
            product_id=product_id,
            category=category,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))