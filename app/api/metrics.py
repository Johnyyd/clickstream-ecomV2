from fastapi import APIRouter, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.core.db_sync import get_db, events_col

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/aggregates")
def get_aggregates(minutes: int = Query(default=60, ge=1, le=10080)) -> Dict[str, Any]:
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
    raw_items: List[Dict[str, Any]] = []
    for d in cur:
        raw_items.append({
            "window_start": d.get("window_start"),
            "window_end": d.get("window_end"),
            "page": d.get("page"),
            "event_type": d.get("event_type"),
            "count": d.get("count", 0),
        })

    print(f"[metrics.get_aggregates] Found {len(raw_items)} raw items from aggregates_minute collection")
    
    # Aggregate items by minute (whether from collection or fallback)
    items: List[Dict[str, Any]] = []
    page_totals = {}
    event_totals = {}
    
    if raw_items:
        # Aggregate existing data from aggregates_minute collection
        minute_totals = {}
        for r in raw_items:
            window_end = r.get("window_end")
            if not window_end:
                continue
            
            # Use window_end as key for grouping
            key = window_end.isoformat() if isinstance(window_end, datetime) else str(window_end)
            
            if key not in minute_totals:
                minute_totals[key] = {
                    "window_start": r.get("window_start"),
                    "window_end": window_end,
                    "count": 0
                }
            
            minute_totals[key]["count"] += r.get("count", 0)
            
            # Track page and event totals
            if r.get("page"):
                page_totals[r["page"]] = page_totals.get(r["page"], 0) + r.get("count", 0)
            if r.get("event_type"):
                event_totals[r["event_type"]] = event_totals.get(r["event_type"], 0) + r.get("count", 0)
        
        # Convert to list
        items = list(minute_totals.values())
        print(f"[metrics.get_aggregates] Aggregated to {len(items)} minute-level items")
        print(f"[metrics.get_aggregates] Top pages: {sorted(page_totals.items(), key=lambda x: x[1], reverse=True)[:3]}")
        
        return {
            "items": items,
            "by_page": page_totals,
            "by_event": event_totals
        }
    
    # Fallback: if no aggregates available, compute from raw events to keep UI populated
    if not items:
        print(f"[metrics.get_aggregates] Using fallback - querying events collection")
        try:
            # Load recent events and bucket by minute, page, event_type
            # Query with datetime (events are stored as datetime in DB, not int)
            q = {"timestamp": {"$gte": since}}
            print(f"[metrics.get_aggregates] Query: {q}, since datetime: {since}")
            cursor = events_col().find(q, {"timestamp": 1, "page": 1, "event_type": 1}).sort("timestamp", 1)
            event_count = 0
            buckets: Dict[str, Dict[str, Dict[str, int]]] = {}
            # buckets[minute_iso][page][event_type] = count
            for ev in cursor:
                event_count += 1
                ts = ev.get("timestamp")
                if not ts:
                    continue
                
                # Handle different timestamp formats
                if isinstance(ts, datetime):
                    # Already datetime - use as-is
                    ts_dt = ts
                elif isinstance(ts, (int, float)):
                    # Unix timestamp - convert to datetime
                    ts_dt = datetime.utcfromtimestamp(ts)
                elif isinstance(ts, str):
                    # ISO string - parse
                    try:
                        ts_dt = datetime.fromisoformat(ts)
                    except Exception:
                        continue
                else:
                    continue
                
                # Floor to minute in UTC (remove timezone info for consistent bucketing)
                ts_utc = ts_dt if ts_dt.tzinfo is None else ts_dt.replace(tzinfo=None)
                minute = ts_utc.replace(second=0, microsecond=0)
                page = ev.get("page") or None
                et = ev.get("event_type") or "pageview"
                mkey = minute.isoformat()
                buckets.setdefault(mkey, {})
                buckets[mkey].setdefault(page, {})
                buckets[mkey][page][et] = buckets[mkey][page].get(et, 0) + 1

            print(f"[metrics.get_aggregates] Processed {event_count} events, created {len(buckets)} minute buckets")
            
            # Convert buckets to items - aggregate by minute for line chart efficiency
            # Group all events in the same minute together for simpler client-side processing
            minute_totals = {}
            page_totals = {}
            event_totals = {}
            
            for mkey in sorted(buckets.keys()):
                minute_dt = datetime.fromisoformat(mkey)
                window_start = minute_dt
                window_end = minute_dt + timedelta(minutes=1)
                
                minute_total = 0
                for page, et_map in buckets[mkey].items():
                    for et, cnt in et_map.items():
                        minute_total += cnt
                        # Track by page and event_type for detailed breakdown if needed
                        page_totals[page] = page_totals.get(page, 0) + cnt
                        event_totals[et] = event_totals.get(et, 0) + cnt
                
                # Store one item per minute with total count
                minute_totals[mkey] = {
                    "window_start": window_start,
                    "window_end": window_end,
                    "count": minute_total
                }
            
            # Create aggregated items: one per minute
            for mkey in sorted(minute_totals.keys()):
                items.append(minute_totals[mkey])
            
            print(f"[metrics.get_aggregates] Generated {len(items)} minute-aggregated items from fallback (from {event_count} raw events)")
            print(f"[metrics.get_aggregates] Top pages: {sorted(page_totals.items(), key=lambda x: x[1], reverse=True)[:3]}")
            print(f"[metrics.get_aggregates] Top events: {sorted(event_totals.items(), key=lambda x: x[1], reverse=True)[:3]}")
            
            # Return with page and event breakdowns for client-side rendering
            return {
                "items": items,
                "by_page": page_totals,
                "by_event": event_totals
            }
        except Exception as e:
            # Log fallback failure
            print(f"[metrics.get_aggregates] Fallback error: {e}")
            import traceback
            traceback.print_exc()

    return {"items": items}
