"""
Machine Learning endpoints for predictions and model management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from app.core.database import db_manager
from app.core.spark import spark_manager
from app.models.user import User
from ..deps import get_db, get_current_user, verify_api_key

router = APIRouter()

@router.get("/models", response_model=List[Dict[str, Any]])
async def list_ml_models(
    model_type: Optional[str] = None,
    status: Optional[str] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List available ML models and their status
    """
    try:
        from app.ml.models import list_models
        
        return await list_models(
            db=db,
            model_type=model_type,
            status=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions/conversion", response_model=Dict[str, Any])
async def predict_conversion(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    features: Optional[Dict[str, Any]] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get conversion probability predictions
    """
    try:
        from app.ml.predictions import predict_conversion_probability
        
        return await predict_conversion_probability(
            db=db,
            user_id=user_id,
            session_id=session_id,
            features=features
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions/churn", response_model=Dict[str, Any])
async def predict_churn(
    user_id: str,
    timeframe: Optional[str] = "30d",
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get churn risk predictions for users
    """
    try:
        from app.ml.predictions import predict_churn_risk
        
        return await predict_churn_risk(
            db=db,
            user_id=user_id,
            timeframe=timeframe
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions/ltv", response_model=Dict[str, Any])
async def predict_lifetime_value(
    user_id: str,
    timeframe: Optional[str] = "1y",
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Predict customer lifetime value
    """
    try:
        from app.ml.predictions import predict_customer_ltv
        
        return await predict_customer_ltv(
            db=db,
            user_id=user_id,
            timeframe=timeframe
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/segments", response_model=List[Dict[str, Any]])
async def get_user_segments(
    algorithm: Optional[str] = "kmeans",
    n_segments: Optional[int] = 5,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user segmentation results
    """
    try:
        from app.ml.segmentation import get_segments
        
        return await get_segments(
            db=db,
            algorithm=algorithm,
            n_segments=n_segments
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns", response_model=List[Dict[str, Any]])
async def get_behavior_patterns(
    pattern_type: Optional[str] = None,
    min_support: Optional[float] = 0.01,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get discovered behavior patterns using pattern mining
    """
    try:
        from app.ml.patterns import get_behavior_patterns
        
        return await get_behavior_patterns(
            db=db,
            pattern_type=pattern_type,
            min_support=min_support
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train", response_model=Dict[str, Any])
async def train_model(
    model_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Train or retrain a ML model
    """
    try:
        from app.ml.training import train_model
        
        return await train_model(
            db=db,
            model_type=model_type,
            parameters=parameters
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/evaluation", response_model=Dict[str, Any])
async def get_model_evaluation(
    model_id: str,
    metrics: Optional[List[str]] = None,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get model evaluation metrics
    """
    try:
        from app.ml.evaluation import evaluate_model
        
        return await evaluate_model(
            db=db,
            model_id=model_id,
            metrics=metrics
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/features", response_model=Dict[str, Any])
async def get_feature_importance(
    model_id: str,
    n_features: Optional[int] = 10,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get feature importance analysis
    """
    try:
        from app.ml.features import get_feature_importance
        
        return await get_feature_importance(
            db=db,
            model_id=model_id,
            n_features=n_features
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deploy", response_model=Dict[str, Any])
async def deploy_model(
    model_id: str,
    environment: str = "production",
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deploy a trained model to specified environment
    """
    try:
        from app.ml.deployment import deploy_model
        
        return await deploy_model(
            db=db,
            model_id=model_id,
            environment=environment
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))