from fastapi import APIRouter, Header
from typing import Optional, Dict, Any
import os
from auth import get_user_by_token
from analysis import run_analysis

router = APIRouter(prefix="/api", tags=["analysis"])

@router.get("/analysis/mode")
def analysis_mode(Authorization: Optional[str] = Header(default=None)):
    # Default to true - Spark is the default engine
    use_spark = str(os.environ.get('USE_SPARK', 'true')).lower() == 'true'
    return {"mode": "spark" if use_spark else "python", "use_spark": use_spark}

@router.post("/analyze")
def analyze(payload: Dict[str, Any], Authorization: Optional[str] = Header(default=None)):
    if not Authorization:
        return {"error": "unauthenticated"}
    user = get_user_by_token(Authorization)
    if not user:
        return {"error": "unauthenticated"}
    
    params = (payload or {}).get("params", {})
    
    # Determine target user for analysis
    # Options: "all" (analyze all users), "username:<name>" (analyze specific user), or None (current user)
    analysis_target = params.get("analysis_target")
    target_user_id = None
    
    if analysis_target == "all":
        # Analyze all users - pass None as user_id
        target_user_id = None
        print(f"[Analysis] Analyzing ALL users in database")
    elif isinstance(analysis_target, str) and analysis_target.startswith("username:"):
        # Analyze specific user by username
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
        # Default: analyze current logged-in user
        target_user_id = str(user["_id"])
        print(f"[Analysis] Analyzing current user: {user.get('username')} (ID: {target_user_id})")
    
    # Run analysis with determined target
    rec = run_analysis(target_user_id, params)
    return {"status": "ok", "analysis": {"_id": str(rec.get("_id", ""))}}
