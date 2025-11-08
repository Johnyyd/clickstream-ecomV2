"""
Event Ingestion API
"""
from fastapi import APIRouter, Depends, Query
from bson import ObjectId
from typing import List, Optional

from app.models.event import Event, EventBatch
from app.services.ingest import ingest_event, ingest_batch
from ..deps import get_db, get_optional_user
from ..models import EventResponse

router = APIRouter()

def _clean_doc(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        else:
            out[k] = v
    return out

@router.post("/", response_model=EventResponse)
async def ingest_single_event(
    event: Event,
    db = Depends(get_db),
    current_user = Depends(get_optional_user)
):
    """
    Ingest single event
    """
    result = await ingest_event(event, db, current_user)
    return result

@router.post("/batch", response_model=List[EventResponse]) 
async def ingest_event_batch(
    batch: EventBatch,
    db = Depends(get_db),
    current_user = Depends(get_optional_user)
):
    """
    Ingest batch of events
    """
    results = await ingest_batch(batch, db, current_user)
    return results

@router.get("/sessions/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    db = Depends(get_db)
):
    """
    Get session event summary
    """
    events_col = db.db["events"]
    try:
        events = list(events_col.find({"session_id": session_id}).sort([("timestamp", 1)]))
        events = [_clean_doc(e) for e in events]
    except Exception:
        events = []
    return {
        "session_id": session_id,
        "event_count": len(events),
        "events": events
    }

@router.get("/sessions/recent")
async def get_recent_sessions(
    limit: int = Query(10, ge=1, le=100),
    db = Depends(get_db)
):
    """
    Get recent sessions
    """
    events_col = db.db["events"]
    sessions: list[dict] = []
    try:
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {"_id": "$session_id", "last_event": {"$first": "$timestamp"}, "user_id": {"$first": "$user_id"}}},
            {"$sort": {"last_event": -1}},
            {"$limit": int(limit)}
        ]
        agg = list(events_col.aggregate(pipeline))
        for d in agg:
            sessions.append({
                "session_id": d.get("_id"),
                "last_event": d.get("last_event"),
                "user_id": str(d.get("user_id")) if isinstance(d.get("user_id"), ObjectId) else d.get("user_id"),
            })
    except Exception:
        sessions = []
    return {"sessions": sessions, "count": len(sessions)}