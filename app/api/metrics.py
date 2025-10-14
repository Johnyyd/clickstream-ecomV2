from fastapi import APIRouter, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta
from db import get_db

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/aggregates")
def get_aggregates(minutes: int = Query(default=60, ge=1, le=1440)) -> Dict[str, Any]:
    """
    Return minute-window aggregates for the last N minutes from Mongo collection `aggregates_minute`.
    Output shape:
    {
      "items": [ { window_start, window_end, page, event_type, count }, ... ]
    }
    """
    db = get_db()
    since = datetime.utcnow() - timedelta(minutes=minutes)
    cur = db.aggregates_minute.find({
        "window_end": {"$gte": since}
    }).sort([("window_end", 1)])
    items: List[Dict[str, Any]] = []
    for d in cur:
        items.append({
            "window_start": d.get("window_start"),
            "window_end": d.get("window_end"),
            "page": d.get("page"),
            "event_type": d.get("event_type"),
            "count": d.get("count", 0),
        })
    return {"items": items}
