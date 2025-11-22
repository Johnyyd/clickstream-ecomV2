from fastapi import APIRouter, Header
from typing import Optional, Dict, Any, List, Tuple
import os
from datetime import datetime, timedelta
import json
import logging
from bson import ObjectId
from threading import Thread
import asyncio

from app.services.auth import get_user_by_token
from app.core.db_sync import events_col, sessions_col, analyses_col
# from app.api.analytics_comprehensive import run_analysis  # TODO: Fix this import
from app.spark.session import get_spark_session
from app.services.analytics import get_user_journey_analysis

router = APIRouter(tags=["analysis"])  # Prefix set in main.py

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _run_spark_analytics_async(analysis_id: ObjectId, username: Optional[str]) -> None:
    try:
        print(f"[Analysis] Starting Spark analytics for analysis_id={analysis_id}, username={username or 'ALL'}")
        start = datetime.utcnow()
        results: Dict[str, Any] = {}
        try:
            from app.spark.seo_analytics import analyze_traffic_sources
            results["seo"] = analyze_traffic_sources(username=username)
            print("[Analysis][seo] done")
        except Exception as e:
            results["seo"] = {"error": str(e)}
            print(f"[Analysis][seo] error: {e}")
        try:
            from app.spark.spark_cart_analytics import analyze_cart_abandonment
            results["cart"] = analyze_cart_abandonment(username=username)
            print("[Analysis][cart] done")
        except Exception as e:
            results["cart"] = {"error": str(e)}
            print(f"[Analysis][cart] error: {e}")
        try:
            from app.spark.spark_retention_analytics import analyze_cohort_retention
            results["retention"] = analyze_cohort_retention(username=username)
            print("[Analysis][retention] done")
        except Exception as e:
            results["retention"] = {"error": str(e)}
            print(f"[Analysis][retention] error: {e}")
        try:
            from app.spark.spark_journey_analytics import analyze_customer_journey
            results["journey"] = analyze_customer_journey(username=username)
            print("[Analysis][journey] done")
        except Exception as e:
            results["journey"] = {"error": str(e)}
            print(f"[Analysis][journey] error: {e}")
        try:
            from app.spark.ml import ml_user_segmentation_kmeans
            results["segmentation"] = ml_user_segmentation_kmeans(username=username)
            print("[Analysis][segmentation] done")
        except Exception as e:
            results["segmentation"] = {"error": str(e)}
            print(f"[Analysis][segmentation] error: {e}")
        try:
            from app.spark.ml import ml_conversion_prediction_tree
            results["conversion"] = ml_conversion_prediction_tree(username=username)
            print("[Analysis][conversion] done")
        except Exception as e:
            results["conversion"] = {"error": str(e)}
            print(f"[Analysis][conversion] error: {e}")
        try:
            from app.spark.ml import ml_purchase_prediction_logistic
            results["purchase"] = ml_purchase_prediction_logistic(username=username)
            print("[Analysis][purchase] done")
        except Exception as e:
            results["purchase"] = {"error": str(e)}
            print(f"[Analysis][purchase] error: {e}")
        try:
            from app.spark.ml import ml_pattern_mining_fpgrowth
            results["patterns"] = ml_pattern_mining_fpgrowth(username=username)
            print("[Analysis][patterns] done")
        except Exception as e:
            results["patterns"] = {"error": str(e)}
            print(f"[Analysis][patterns] error: {e}")
        try:
            from app.spark.recommendation_als import ml_product_recommendations_als
            if username:
                results["recommendations"] = ml_product_recommendations_als(username=username, top_n=50)
            else:
                results["recommendations"] = ml_product_recommendations_als(username=None, top_n=50)
            print("[Analysis][recommendations] done")
        except Exception as e:
            results["recommendations"] = {"error": str(e)}
            print(f"[Analysis][recommendations] error: {e}")

        # Generate LLM insights summarizing ML outputs (best-effort)
        llm_insights: Dict[str, Any] | None = None
        try:
            from app.services.openrouter import analyze_ml_results
            llm_insights = asyncio.run(analyze_ml_results(results))
            print("[Analysis][llm_insights] done")
        except Exception as e:
            llm_insights = {"error": str(e)}
            print(f"[Analysis][llm_insights] error: {e}")

        end = datetime.utcnow()
        duration = (end - start).total_seconds()
        analyses_col().update_one(
            {"_id": analysis_id},
            {"$set": {
                "summary": {"status": "completed", "duration_seconds": duration},
                "results": results,
                "llm_insights": llm_insights,
                "completed_at": end
            }}
        )
        print(f"[Analysis] Completed analysis_id={analysis_id} in {duration:.2f}s")
    except Exception as e:
        try:
            analyses_col().update_one(
                {"_id": analysis_id},
                {"$set": {"summary": {"status": "failed", "error": str(e)}, "completed_at": datetime.utcnow()}}
            )
        finally:
            print(f"[Analysis] Failed analysis_id={analysis_id}: {e}")

@router.get("/analysis/mode")
def analysis_mode(Authorization: Optional[str] = Header(default=None)):
    # Default to true - Spark is the default engine
    use_spark = str(os.environ.get('USE_SPARK', 'true')).lower() == 'true'
    return {"mode": "spark" if use_spark else "python", "use_spark": use_spark}

@router.post("/analyze")
def analyze(payload: Dict[str, Any], Authorization: Optional[str] = Header(default=None)):
    try:
        if not Authorization:
            return {"error": "unauthenticated"}
        user = get_user_by_token(Authorization)
        if not user:
            return {"error": "unauthenticated"}

        params = (payload or {}).get("params", {})
        analysis_target = params.get("analysis_target")
        target_user_id = None

        if analysis_target == "all":
            target_user_id = None
            print(f"[Analysis] Analyzing ALL users in database")
        elif isinstance(analysis_target, str) and analysis_target.startswith("username:"):
            target_username = analysis_target.split(":", 1)[1].strip()
            if target_username:
                from app.repositories.users_repo import UsersRepository
                target_user = UsersRepository().find_by_username(target_username)
                if not target_user:
                    return {"error": f"User '{target_username}' not found"}
                target_user_id = target_user["_id"]
                print(f"[Analysis] Analyzing user: {target_username} (ID: {target_user_id})")
            else:
                return {"error": "Username cannot be empty"}
        else:
            target_user_id = str(user["_id"])
            print(f"[Analysis] Analyzing current user: {user.get('username')} (ID: {target_user_id})")

        try:
            doc: Dict[str, Any] = {
                "user_id": (ObjectId(target_user_id) if target_user_id else None),
                "created_at": datetime.utcnow(),
                "mode": "spark" if str(os.environ.get('USE_SPARK', 'true')).lower() == 'true' else "python",
                "summary": {
                    "status": "stub",
                    "message": "Analysis queued/stubbed"
                },
                "results": {}
            }
            ins = analyses_col().insert_one(doc)
            username_for_modules: Optional[str] = None
            if analysis_target == "all":
                username_for_modules = None
            elif isinstance(analysis_target, str) and analysis_target.startswith("username:"):
                username_for_modules = analysis_target.split(":", 1)[1].strip() or None
            else:
                username_for_modules = user.get("username")

            print(f"[Analysis] Queued analysis_id={ins.inserted_id} (spark) for target={username_for_modules or 'ALL'}")
            t = Thread(target=_run_spark_analytics_async, args=(ins.inserted_id, username_for_modules), daemon=True)
            t.start()
            return {"analysis": {"_id": str(ins.inserted_id)}}
        except Exception:
            # Fallback return to keep frontend flow
            return {"analysis": {"_id": "temp"}}
    except Exception as e:
        return {"error": "INTERNAL_ERROR", "message": str(e)}
