from fastapi import APIRouter, Header
from typing import Optional, Dict, Any, List, Tuple
import os
from datetime import datetime, timedelta
import json
import logging
from bson import ObjectId

from app.services.auth import get_user_by_token
from app.core.db_sync import events_col, sessions_col, analyses_col
# from app.api.analytics_comprehensive import run_analysis  # TODO: Fix this import
from app.spark.session import get_spark_session
from app.services.analytics import get_user_journey_analysis

router = APIRouter(tags=["analysis"])  # Prefix set in main.py

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            return {"analysis": {"_id": str(ins.inserted_id)}}
        except Exception:
            # Fallback return to keep frontend flow
            return {"analysis": {"_id": "temp"}}
    except Exception as e:
        return {"error": "INTERNAL_ERROR", "message": str(e)}
