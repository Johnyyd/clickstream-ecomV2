# ingest.py
from db import events_col, sessions_col
from datetime import datetime
import uuid
import time
import pytz

def ingest_event(event_json):
    """
    event_json example:
    {
      "client_id": "uuid",
      "timestamp": 1690000000,   # unix epoch optional
      "page": "/home",
      "event_type": "pageview",
      "properties": {...},
      "user_id": "<optional user id string>",
      "session_id": "<optional session id string>"
    }
    """
    ts = event_json.get("timestamp")
    if ts:
        ts = datetime.fromtimestamp(ts, tz=pytz.UTC)
    else:
        ts = datetime.now(pytz.UTC)
    
    # Ensure user_id and session_id are properly handled
    user_id = event_json.get("user_id")
    session_id = event_json.get("session_id")

    # If user_id is provided but session_id is not, create a consistent session_id
    if user_id and not session_id:
        if hasattr(user_id, '__str__'):
            session_id = f"session_{str(user_id)[-6:]}_{int(time.time())}"
        else:
            session_id = f"session_{user_id}_{int(time.time())}"
    # Normalize to string for consistent keying in both events and sessions
    if session_id is not None:
        session_id = str(session_id)
    
    doc = {
        "client_id": event_json.get("client_id", str(uuid.uuid4())),
        "timestamp": ts,
        "page": event_json.get("page"),
        "event_type": event_json.get("event_type","pageview"),
        "properties": event_json.get("properties", {}),
        "user_id": user_id,  # Keep as-is (ObjectId or string)
        "session_id": session_id or str(uuid.uuid4())
    }
    res = events_col().insert_one(doc)

    # Upsert session document so sessions are persisted in DB
    try:
        sessions_col().update_one(
            {"session_id": doc["session_id"]},
            {
                "$setOnInsert": {
                    "session_id": doc["session_id"],
                    "user_id": user_id,
                    "client_id": doc.get("client_id"),
                    "created_at": ts,
                    "first_event_at": ts,
                    "pages": [],
                },
                "$max": {"last_event_at": ts},
                "$min": {"first_event_at": ts},
                "$inc": {"event_count": 1},
                # For a lightweight trace of pages (optional, capped by client)
                # We avoid $addToSet here to keep cost low; can be enabled if needed.
            },
            upsert=True,
        )
    except Exception:
        # Do not block ingestion if session upsert fails
        pass

    return res.inserted_id
