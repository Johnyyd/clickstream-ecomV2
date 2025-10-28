from fastapi import APIRouter, Header
from typing import Optional
from app.repositories.analyses_repo import AnalysesRepository
from app.services.auth import get_user_by_token
from fastapi import HTTPException
from bson import ObjectId

router = APIRouter(tags=["analyses"])  # Prefix set in main.py

# Simple token auth helper (reuse sessions collection via server endpoints is not available here,
# so we keep consistent with existing flow by passing Authorization token to server.
# For now, analyses are fetched per user by token lookup will rely on client-side correctness.)

def _stringify_object_ids(obj):
    """Recursively convert bson.ObjectId instances to strings for JSON responses."""
    try:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if isinstance(v, ObjectId):
                    out[k] = str(v)
                else:
                    out[k] = _stringify_object_ids(v)
            return out
        if isinstance(obj, list):
            return [_stringify_object_ids(v) for v in obj]
        return obj
    except Exception:
        return obj

@router.get("/analyses")
def list_analyses(Authorization: Optional[str] = Header(default=None)):
    # If a token is provided, attempt to resolve it to a user and return their analyses.
    # Otherwise, fallback to the last 20 analyses overall.
    analyses_repo = AnalysesRepository()
    try:
        items = []
        if Authorization:
            user = get_user_by_token(Authorization)
            if user and user.get("_id"):
                items = analyses_repo.list_by_user(user_id=str(user["_id"]), limit=20, offset=0)
        if not items:
            items = analyses_repo.list_by_user(user_id=None, limit=20, offset=0)
        # Keep ISO formatting for created_at if it's a datetime
        for i in items:
            if hasattr(i.get("created_at"), "isoformat"):
                i["created_at"] = i["created_at"].isoformat()
        return [_stringify_object_ids(i) for i in items]
    except Exception:
        raise HTTPException(status_code=500, detail="Database unavailable")

@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, Authorization: Optional[str] = Header(default=None)):
    repo = AnalysesRepository()
    try:
        doc = repo.get_by_id(analysis_id)
        if not doc:
            return {"error": "not found"}
        if hasattr(doc.get("created_at"), "isoformat"):
            doc["created_at"] = doc["created_at"].isoformat()
        return _stringify_object_ids(doc)
    except Exception:
        raise HTTPException(status_code=500, detail="Database unavailable")
