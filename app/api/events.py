from fastapi import APIRouter, Query
from app.models.events import Event, EventIngestResponse, EventBatch, EventBatchResponse
from ingest import ingest_event
from db import events_col, sessions_col
from datetime import datetime

router = APIRouter(prefix="/api", tags=["events"])

@router.post("/ingest", response_model=EventIngestResponse)
def ingest(evt: Event):
    eid = ingest_event(evt.model_dump())
    return {"event_id": str(eid)}

@router.post("/ingest-batch", response_model=EventBatchResponse)
def ingest_batch(batch: EventBatch):
    ids = []
    for e in batch.events:
        eid = ingest_event(e.model_dump())
        ids.append(str(eid))
    return {"inserted": len(ids), "ids": ids}

# --- Verification endpoints ---
@router.get("/sessions/{session_id}/summary")
def session_summary(session_id: str):
    col_e = events_col()
    col_s = sessions_col()
    # Try new primary key layout (_id == session_id); fallback to legacy session_id field
    sess = col_s.find_one({"_id": str(session_id)}) or col_s.find_one({"session_id": str(session_id)})
    cnt = col_e.count_documents({"session_id": str(session_id)})
    # Pull min/max timestamps and distinct session_ids seen in events for sanity
    agg = list(col_e.aggregate([
        {"$match": {"session_id": str(session_id)}},
        {"$group": {"_id": "$session_id", "min_ts": {"$min": "$timestamp"}, "max_ts": {"$max": "$timestamp"}, "pages": {"$addToSet": "$page"}}}
    ]))
    summary = {
        "session_exists": bool(sess),
        "events_count": cnt,
        "session_doc": {
            "_id": sess.get("_id") if sess else None,
            "session_id": sess.get("session_id") if sess else None,
            "user_id": str(sess.get("user_id")) if sess and sess.get("user_id") is not None else None,
            "first_event_at": sess.get("first_event_at").isoformat() if sess and isinstance(sess.get("first_event_at"), datetime) else None,
            "last_event_at": sess.get("last_event_at").isoformat() if sess and isinstance(sess.get("last_event_at"), datetime) else None,
        },
        "events_window": {
            "first": agg[0].get("min_ts").isoformat() if agg and isinstance(agg[0].get("min_ts"), datetime) else None,
            "last": agg[0].get("max_ts").isoformat() if agg and isinstance(agg[0].get("max_ts"), datetime) else None,
            "pages_sample": (agg[0].get("pages") or [])[:10] if agg else [],
        }
    }
    return summary

@router.get("/sessions/recent")
def recent_sessions(limit: int = Query(10, ge=1, le=100)):
    col_s = sessions_col()
    col_e = events_col()
    docs = list(col_s.find({}, sort=[("last_event_at", -1)], limit=limit))
    out = []
    for s in docs:
        sid = s.get("session_id")
        cnt = col_e.count_documents({"session_id": sid})
        out.append({
            "session_id": sid,
            "user_id": str(s.get("user_id")) if s.get("user_id") is not None else None,
            "first_event_at": s.get("first_event_at").isoformat() if isinstance(s.get("first_event_at"), datetime) else None,
            "last_event_at": s.get("last_event_at").isoformat() if isinstance(s.get("last_event_at"), datetime) else None,
            "events_count": cnt,
        })
    return {"items": out}
