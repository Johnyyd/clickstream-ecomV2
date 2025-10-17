from fastapi import APIRouter, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta
from db import get_db, events_col

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
    }).sort([( "window_end", 1 )])
    items: List[Dict[str, Any]] = []
    for d in cur:
        items.append({
            "window_start": d.get("window_start"),
            "window_end": d.get("window_end"),
            "page": d.get("page"),
            "event_type": d.get("event_type"),
            "count": d.get("count", 0),
        })

    # Fallback: if no aggregates available, compute from raw events to keep UI populated
    if not items:
        try:
            # Load recent events and bucket by minute, page, event_type
            q = {"timestamp": {"$gte": since}}
            cursor = events_col().find(q, {"timestamp": 1, "page": 1, "event_type": 1}).sort("timestamp", 1)
            buckets: Dict[str, Dict[str, Dict[str, int]]] = {}
            # buckets[minute_iso][page][event_type] = count
            for ev in cursor:
                ts = ev.get("timestamp")
                if not ts:
                    continue
                # Ensure ts is datetime
                if isinstance(ts, (int, float)):
                    ts = datetime.utcfromtimestamp(ts)
                elif isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except Exception:
                        continue
                # Floor to minute in UTC
                ts_utc = ts if ts.tzinfo is None else ts.astimezone(tz=None).replace(tzinfo=None)
                minute = ts_utc.replace(second=0, microsecond=0)
                page = ev.get("page") or None
                et = ev.get("event_type") or "pageview"
                mkey = minute.isoformat()
                buckets.setdefault(mkey, {})
                buckets[mkey].setdefault(page, {})
                buckets[mkey][page][et] = buckets[mkey][page].get(et, 0) + 1

            # Convert buckets to items sorted by window_end ascending
            for mkey in sorted(buckets.keys()):
                minute_dt = datetime.fromisoformat(mkey)
                window_start = minute_dt
                window_end = minute_dt + timedelta(minutes=1)
                for page, et_map in buckets[mkey].items():
                    for et, cnt in et_map.items():
                        items.append({
                            "window_start": window_start,
                            "window_end": window_end,
                            "page": page,
                            "event_type": et,
                            "count": int(cnt),
                        })
        except Exception:
            # Silent fallback failure; return empty items
            pass

    return {"items": items}
