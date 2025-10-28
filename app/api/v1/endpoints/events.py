"""
Event Ingestion API
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from app.models.event import Event, EventBatch
from app.services.ingest import ingest_event, ingest_batch
from ..deps import get_db, get_optional_user
from ..models import EventResponse

router = APIRouter()

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
    events = await db.events.get_session_events(session_id)
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
    sessions = await db.events.get_recent_sessions(limit)
    return {
        "sessions": sessions,
        "count": len(sessions)
    }