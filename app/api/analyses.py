from fastapi import APIRouter, Header
from typing import Optional
from app.repositories.analyses_repo import AnalysesRepository

router = APIRouter(prefix="/api", tags=["analyses"])

# Simple token auth helper (reuse sessions collection via server endpoints is not available here,
# so we keep consistent with existing flow by passing Authorization token to server.
# For now, analyses are fetched per user by token lookup will rely on client-side correctness.)

@router.get("/analyses")
def list_analyses(Authorization: Optional[str] = Header(default=None)):
    # In the legacy server, token is resolved to user; here we fallback to returning last 20 analyses
    repo = AnalysesRepository()
    items = repo.list_by_user(user_id=None, limit=20, offset=0)
    # Keep ISO formatting for created_at if it's a datetime
    for i in items:
        if hasattr(i.get("created_at"), "isoformat"):
            i["created_at"] = i["created_at"].isoformat()
    return items

@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, Authorization: Optional[str] = Header(default=None)):
    repo = AnalysesRepository()
    doc = repo.get_by_id(analysis_id)
    if not doc:
        return {"error": "not found"}
    if hasattr(doc.get("created_at"), "isoformat"):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc
