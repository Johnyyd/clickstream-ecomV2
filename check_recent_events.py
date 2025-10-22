"""
Quick script to check recent events in MongoDB
"""
from datetime import datetime, timedelta
from db import events_col
import pytz

def check_events():
    col = events_col()
    
    # Get total count
    total = col.count_documents({})
    print(f"Total events in DB: {total}")
    
    # Get last 10 events
    recent = list(col.find({}).sort("timestamp", -1).limit(10))
    print(f"\nLast 10 events:")
    for i, ev in enumerate(recent, 1):
        ts = ev.get("timestamp")
        if isinstance(ts, int):
            dt = datetime.fromtimestamp(ts, tz=pytz.UTC)
        else:
            dt = ts
        print(f"{i}. {ev.get('event_type')} on {ev.get('page')} at {dt} (raw: {ts})")
    
    # Check events in last 60 minutes
    now = datetime.utcnow()
    since = now - timedelta(minutes=60)
    since_ts = int(since.timestamp())
    
    print(f"\nCurrent UTC time: {now}")
    print(f"Query since: {since} (timestamp: {since_ts})")
    
    # Query with timestamp as int
    count_int = col.count_documents({"timestamp": {"$gte": since_ts}})
    print(f"Events in last 60min (timestamp >= {since_ts}): {count_int}")
    
    # Also try querying recent events by any timestamp
    if recent:
        latest_ts = recent[0].get("timestamp")
        if isinstance(latest_ts, int):
            # Try 5 minutes before latest
            five_min_ago = latest_ts - 300
            count_recent = col.count_documents({"timestamp": {"$gte": five_min_ago}})
            print(f"Events since {five_min_ago} (5min before latest): {count_recent}")

if __name__ == "__main__":
    check_events()
