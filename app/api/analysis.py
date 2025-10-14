from fastapi import APIRouter, Header
from typing import Optional, Dict, Any
import os
from auth import get_user_by_token
from analysis import run_analysis

router = APIRouter(prefix="/api", tags=["analysis"])

@router.get("/analysis/mode")
def analysis_mode(Authorization: Optional[str] = Header(default=None)):
    use_spark = str(os.environ.get('USE_SPARK', 'false')).lower() == 'true'
    return {"mode": "spark" if use_spark else "python", "use_spark": use_spark}

@router.post("/analyze")
def analyze(payload: Dict[str, Any], Authorization: Optional[str] = Header(default=None)):
    if not Authorization:
        return {"error": "unauthenticated"}
    user = get_user_by_token(Authorization)
    if not user:
        return {"error": "unauthenticated"}
    params = (payload or {}).get("params", {})
    rec = run_analysis(str(user["_id"]), params)
    return {"status": "ok", "analysis": {"_id": str(rec.get("_id", ""))}}
