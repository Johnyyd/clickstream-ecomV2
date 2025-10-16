# ingest.py
from db import events_col, sessions_col
from datetime import datetime
import uuid
import time
import pytz
import os

_KAFKA_BROKERS = os.getenv("KAFKA_BROKERS")
_KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "clickstream.events")
_kafka_producer = None

def _get_kafka_producer():
    global _kafka_producer
    if not _KAFKA_BROKERS:
        return None
    if _kafka_producer is None:
        try:
            from kafka import KafkaProducer
            _kafka_producer = KafkaProducer(bootstrap_servers=_KAFKA_BROKERS.split(","), value_serializer=lambda v: v.encode("utf-8"))
        except Exception:
            _kafka_producer = None
    return _kafka_producer

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

    # Optional forward to Kafka (best-effort, non-blocking)
    try:
        producer = _get_kafka_producer()
        if producer:
            import json as _json
            payload = {
                "client_id": doc.get("client_id"),
                "session_id": doc.get("session_id"),
                "user_id": str(doc.get("user_id")) if doc.get("user_id") is not None else None,
                "page": doc.get("page"),
                "event_type": doc.get("event_type"),
                "properties": doc.get("properties", {}),
                "timestamp": ts.timestamp(),
            }
            producer.send(_KAFKA_TOPIC, _json.dumps(payload))
    except Exception:
        pass

    # Upsert browsing session document using _id == session_id (primary key)
    try:
        sessions_col().update_one(
            {"_id": doc["session_id"]},
            {
                "$setOnInsert": {
                    "session_id": doc["session_id"],
                    "user_id": user_id,
                    "client_id": doc.get("client_id"),
                    "created_at": ts,
                    "pages": [],
                },
                "$max": {"last_event_at": ts},
                "$min": {"first_event_at": ts},
                "$inc": {"event_count": 1},
                "$addToSet": {"pages": doc.get("page")},
            },
            upsert=True,
        )
    except Exception:
        # Do not block ingestion if session upsert fails
        pass

    return res.inserted_id
