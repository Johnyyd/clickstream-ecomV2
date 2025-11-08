"""
ML API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.api.v1.deps import get_current_user
import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()  # Prefix set in main.py

# Thread pool for running ML tasks
executor = ThreadPoolExecutor(max_workers=2)

class MLRequest(BaseModel):
    username: Optional[str] = None


@router.post("/ml/kmeans")
async def run_kmeans(request: MLRequest, current_user: dict = Depends(get_current_user)):
    """Run K-Means user segmentation"""
    try:
        from app.spark.ml import ml_user_segmentation_kmeans
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            ml_user_segmentation_kmeans,
            request.username
        )
        
        # Check if result contains an error
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ml/decision-tree")
async def run_decision_tree(request: MLRequest, current_user: dict = Depends(get_current_user)):
    """Run Decision Tree conversion prediction"""
    try:
        from app.spark.ml import ml_conversion_prediction_tree
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            ml_conversion_prediction_tree,
            request.username
        )
        
        # Check if result contains an error
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ml/fp-growth")
async def run_fpgrowth(request: MLRequest, current_user: dict = Depends(get_current_user)):
    """Run FP-Growth pattern mining"""
    try:
        from app.spark.ml import ml_pattern_mining_fpgrowth
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            ml_pattern_mining_fpgrowth,
            request.username
        )
        
        # Check if result contains an error
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ml/logistic-regression")
async def run_logistic_regression(request: MLRequest, current_user: dict = Depends(get_current_user)):
    """Run Logistic Regression purchase prediction"""
    try:
        from app.spark.ml import ml_purchase_prediction_logistic
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            ml_purchase_prediction_logistic,
            request.username
        )
        
        # Check if result contains an error
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
