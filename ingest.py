# ingest.py
from db import events_col
from datetime import datetime
import uuid

def ingest_event(event_json):
    """
    event_json example:
    {
      "client_id": "uuid",
      "timestamp": 1690000000,   # unix epoch optional
      "page": "/home",
      "event_type": "pageview",
      "properties": {...},
      "user_id": "<optional user id string>"
    }
    """
    ts = event_json.get("timestamp")
    if ts:
        ts = datetime.utcfromtimestamp(ts)
    else:
        ts = datetime.utcnow()
    doc = {
        "client_id": event_json.get("client_id", str(uuid.uuid4())),
        "timestamp": ts,
        "page": event_json.get("page"),
        "event_type": event_json.get("event_type","pageview"),
        "properties": event_json.get("properties", {}),
        "user_id": event_json.get("user_id"),
        "session_id": event_json.get("session_id") or str(uuid.uuid4())
    }
    res = events_col().insert_one(doc)
    return res.inserted_id
