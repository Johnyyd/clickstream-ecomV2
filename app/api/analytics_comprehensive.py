"""
API Router for Comprehensive Analytics
Exposes all analytics modules via REST API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import traceback

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class AnalyticsRequest(BaseModel):
    username: Optional[str] = None
    limit: Optional[int] = None
    modules: List[str] = ["all"]  # seo, cart, retention, journey, recommendations, ml


@router.get("/seo")
async def get_seo_analysis(username: Optional[str] = None):
    """
    SEO & Traffic Source Analysis
    - Traffic by source
    - Landing page effectiveness
    - Conversion by source
    """
    try:
        from spark_seo_analytics import analyze_traffic_sources
        result = analyze_traffic_sources(username=username)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cart-abandonment")
async def get_cart_abandonment(username: Optional[str] = None):
    """
    Cart Abandonment Analysis
    - Abandonment rate
    - Most abandoned products
    - Cart value analysis
    """
    try:
        from spark_cart_analytics import analyze_cart_abandonment
        result = analyze_cart_abandonment(username=username)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retention")
async def get_retention_analysis(username: Optional[str] = None):
    """
    Cohort & Retention Analysis
    - Cohorts by signup date
    - Retention rates
    - User segments
    """
    try:
        from spark_retention_analytics import analyze_cohort_retention
        result = analyze_cohort_retention(username=username)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customer-journey")
async def get_customer_journey(username: Optional[str] = None):
    """
    Customer Journey Path Analysis
    - Conversion paths
    - Drop-off points
    - Common sequences
    """
    try:
        from spark_journey_analytics import analyze_customer_journey
        result = analyze_customer_journey(username=username)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/{username}")
async def get_product_recommendations(
    username: str,
    top_n: int = Query(default=5, ge=1, le=20)
):
    """
    Product Recommendations using ALS - For Specific User
    - Personalized recommendations
    - Predicted ratings
    """
    try:
        from spark_recommendation_als import ml_product_recommendations_als
        result = ml_product_recommendations_als(username=username, top_n=top_n)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_all_recommendations(
    top_n: int = Query(default=5, ge=1, le=20)
):
    """
    Product Recommendations using ALS - For All Users
    - Sample recommendations from all users
    - Top-N predictions per user
    """
    try:
        from spark_recommendation_als import ml_product_recommendations_als
        result = ml_product_recommendations_als(username=None, top_n=top_n)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-segmentation")
async def get_user_segmentation(username: Optional[str] = None):
    """
    User Segmentation using K-Means
    - User clusters by behavior
    - Cluster statistics
    """
    try:
        from spark_ml import ml_user_segmentation_kmeans
        result = ml_user_segmentation_kmeans(username=username)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversion-prediction")
async def get_conversion_prediction(username: Optional[str] = None):
    """
    Conversion Prediction using Decision Tree
    - Purchase likelihood
    - Feature importance
    """
    try:
        from spark_ml import ml_conversion_prediction_tree
        result = ml_conversion_prediction_tree(username=username)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchase-probability")
async def get_purchase_probability(username: Optional[str] = None):
    """
    Purchase Probability using Logistic Regression
    - Purchase probability scores
    - Feature coefficients
    """
    try:
        from spark_ml import ml_purchase_prediction_logistic
        result = ml_purchase_prediction_logistic(username=username)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pattern-mining")
async def get_pattern_mining(username: Optional[str] = None):
    """
    Pattern Mining using FP-Growth
    - Frequent page patterns
    - Association rules
    """
    try:
        from spark_ml import ml_pattern_mining_fpgrowth
        result = ml_pattern_mining_fpgrowth(username=username)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comprehensive")
async def run_comprehensive_analysis(request: AnalyticsRequest):
    """
    Run comprehensive analytics across all modules
    Returns combined results from requested modules
    """
    try:
        results = {
            "username": request.username,
            "modules_requested": request.modules,
            "results": {}
        }
        
        modules = request.modules if request.modules != ["all"] else [
            "seo", "cart", "retention", "journey", "recommendations", 
            "segmentation", "conversion", "purchase", "patterns"
        ]
        
        for module in modules:
            try:
                if module == "seo":
                    from spark_seo_analytics import analyze_traffic_sources
                    results["results"]["seo"] = analyze_traffic_sources(username=request.username)
                
                elif module == "cart":
                    from spark_cart_analytics import analyze_cart_abandonment
                    results["results"]["cart"] = analyze_cart_abandonment(username=request.username)
                
                elif module == "retention":
                    from spark_retention_analytics import analyze_cohort_retention
                    results["results"]["retention"] = analyze_cohort_retention(username=request.username)
                
                elif module == "journey":
                    from spark_journey_analytics import analyze_customer_journey
                    results["results"]["journey"] = analyze_customer_journey(username=request.username)
                
                elif module == "recommendations" and request.username:
                    from spark_recommendation_als import ml_product_recommendations_als
                    results["results"]["recommendations"] = ml_product_recommendations_als(
                        username=request.username, top_n=5
                    )
                
                elif module == "segmentation":
                    from spark_ml import ml_user_segmentation_kmeans
                    results["results"]["segmentation"] = ml_user_segmentation_kmeans(username=request.username)
                
                elif module == "conversion":
                    from spark_ml import ml_conversion_prediction_tree
                    results["results"]["conversion"] = ml_conversion_prediction_tree(username=request.username)
                
                elif module == "purchase":
                    from spark_ml import ml_purchase_prediction_logistic
                    results["results"]["purchase"] = ml_purchase_prediction_logistic(username=request.username)
                
                elif module == "patterns":
                    from spark_ml import ml_pattern_mining_fpgrowth
                    results["results"]["patterns"] = ml_pattern_mining_fpgrowth(username=request.username)
                
            except Exception as e:
                results["results"][module] = {"error": str(e)}
                print(f"Error in module {module}: {e}")
        
        return results
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def analytics_health():
    """Check analytics modules health"""
    health = {
        "status": "healthy",
        "modules": {}
    }
    
    # Check each module
    modules_to_check = [
        ("spark_seo_analytics", "SEO Analytics"),
        ("spark_cart_analytics", "Cart Analytics"),
        ("spark_retention_analytics", "Retention Analytics"),
        ("spark_journey_analytics", "Journey Analytics"),
        ("spark_recommendation_als", "ALS Recommendations"),
        ("spark_ml", "ML Models")
    ]
    
    for module_name, display_name in modules_to_check:
        try:
            __import__(module_name)
            health["modules"][display_name] = "available"
        except Exception as e:
            health["modules"][display_name] = f"error: {str(e)}"
            health["status"] = "degraded"
    
    return health
