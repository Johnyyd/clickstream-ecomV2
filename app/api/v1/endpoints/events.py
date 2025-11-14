"""
Event Ingestion API
"""
from fastapi import APIRouter, Depends, Query
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timezone

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

def _clean_mongo_value(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, list):
        return [_clean_mongo_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _clean_mongo_value(x) for k, x in v.items()}
    return v

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
    limit: int = Query(10, ge=1, le=500),
    user: Optional[str] = Query(None, description="Filter by user id substring (case-insensitive)"),
    db = Depends(get_db)
):
    """
    Get recent sessions
    """
    events_col = db.db["events"]
    sessions: list[dict] = []
    try:
        pipeline = [{"$sort": {"timestamp": -1}}]
        if user:
            # Match by substring against stringified user_id to support ObjectId or string ids
            pipeline += [
                {"$addFields": {"user_id_str": {"$toString": "$user_id"}}},
                {"$match": {"user_id_str": {"$regex": user, "$options": "i"}}},
            ]
        pipeline += [
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

@router.get("/activity")
async def get_activity_histograms(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    tz_offset_minutes: int = 0,
    db = Depends(get_db)
):
    """
    Return activity histograms within the specified date range.
    - hourly: array of 24 counts for hours 0..23 (UTC)
    - dow: array of 7 counts for Sun..Sat (Mongo $dayOfWeek: 1=Sun..7=Sat)
    """
    events_col = db.db["events"]
    # Defaults to last 30 days if not provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        from datetime import timedelta
        start_date = end_date - timedelta(days=30)
    # Normalize to naive UTC for Mongo comparisons
    try:
        if end_date and getattr(end_date, 'tzinfo', None) is not None:
            end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)
        if start_date and getattr(start_date, 'tzinfo', None) is not None:
            start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        pass
    hourly = [0]*24
    dow = [0]*7
    by_date: list[dict] = []
    peak_day_label: str | None = None
    try:
        pipeline = [
            # Compute tsDate field for consistent matching and bucketing
            {"$addFields": {
                # tsRaw giữ giá trị thời gian gốc để debug
                "tsRaw": {"$ifNull": [
                    "$occurred_at",
                    {"$ifNull": [
                        "$processed_at",
                        {"$ifNull": [
                            "$occurred_at_iso",
                            "$timestamp"
                        ]}
                    ]}
                ]},
                # tsDate: chuyển mọi kiểu (date/number/string) sang Date an toàn
                "tsDate": {
                    "$convert": {
                        "input": {"$ifNull": [
                            "$occurred_at",
                            {"$ifNull": [
                                "$processed_at",
                                {"$ifNull": [
                                    "$occurred_at_iso",
                                    "$timestamp"
                                ]}
                            ]}
                        ]},
                        "to": "date",
                        "onError": None,
                        "onNull": None
                    }
                }
            }},
            {"$facet": {
                "hourly": [
                    {"$match": {"tsDate": {"$gte": start_date, "$lte": end_date}}},
                    {"$addFields": {"_ts_local": {"$add": ["$tsDate", {"$multiply": [-1, tz_offset_minutes, 60000]}]}}},
                    {"$group": {"_id": {"$hour": "$_ts_local"}, "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}}
                ],
                "dow": [
                    {"$match": {"tsDate": {"$gte": start_date, "$lte": end_date}}},
                    {"$addFields": {"_ts_local": {"$add": ["$tsDate", {"$multiply": [-1, tz_offset_minutes, 60000]}]}}},
                    {"$group": {"_id": {"$dayOfWeek": "$_ts_local"}, "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}}
                ],
                "by_date": [
                    {"$match": {"tsDate": {"$gte": start_date, "$lte": end_date}}},
                    {"$addFields": {"_ts_local": {"$add": ["$tsDate", {"$multiply": [-1, tz_offset_minutes, 60000]}]}}},
                    {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$_ts_local"}}, "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}}
                ],
                "debug_sample": [
                    {"$project": {"tsRaw": 1, "tsDate": 1, "timestamp": 1, "occurred_at": 1, "processed_at": 1, "occurred_at_iso": 1}},
                    {"$limit": 5}
                ]
            }}
        ]
        res = list(events_col.aggregate(pipeline))
        if res:
            fac = res[0]
            for r in (fac.get("hourly") or []):
                try:
                    h = int(r.get("_id", 0))
                    if 0 <= h <= 23:
                        hourly[h] = int(r.get("count", 0) or 0)
                except Exception:
                    pass
            # Mongo dayOfWeek: 1..7 -> Sun..Sat -> map to 0..6
            for r in (fac.get("dow") or []):
                try:
                    d = int(r.get("_id", 1)) - 1
                    if 0 <= d <= 6:
                        dow[d] = int(r.get("count", 0) or 0)
                except Exception:
                    pass
            # By date series and peak day
            by_date = [{"date": x.get("_id"), "count": int(x.get("count", 0) or 0)} for x in (fac.get("by_date") or [])]
            if by_date:
                m = max(by_date, key=lambda x: x.get("count", 0) or 0)
                peak_day_label = m.get("date")
    except Exception:
        res = []
    debug_sample_raw = []
    if 'res' in locals() and res:
        try:
            debug_sample_raw = res[0].get("debug_sample") or []
        except Exception:
            debug_sample_raw = []
    debug_sample = _clean_mongo_value(debug_sample_raw)
    return {"hourly": hourly, "dow": dow, "by_date": by_date, "peak_day": peak_day_label, "start_date": start_date, "end_date": end_date, "debug_sample": debug_sample}