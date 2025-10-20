# ingest.py
from db import events_col, sessions_col
from bson import ObjectId
from datetime import datetime
import uuid
import time
import pytz
import os
from pymongo import ReturnDocument

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

    if user_id and not session_id:
        session_id = str(ObjectId())
    if session_id is not None:
        session_id = str(session_id)
    
    # Coerce user_id to ObjectId when possible, else None
    try:
        if user_id is not None:
            user_id = ObjectId(str(user_id))
    except Exception:
        user_id = None

    doc = {
        "client_id": event_json.get("client_id", str(uuid.uuid4())),
        "timestamp": ts,
        "page": event_json.get("page"),
        "event_type": event_json.get("event_type","pageview"),
        "properties": event_json.get("properties", {}),
        "user_id": user_id,
        "session_id": session_id
    }
    # Upsert/find the browsing session by its string session_id, let Mongo assign ObjectId _id
    try:
        session_doc = sessions_col().find_one_and_update(
            {"session_id": doc["session_id"]},
            {
                "$setOnInsert": {
                    "session_id": doc["session_id"],
                    "user_id": user_id,
                    # Don't set pages here - let $addToSet handle it
                },
                "$set": {"client_id": doc.get("client_id")},
                "$max": {"last_event_at": ts},
                "$min": {"first_event_at": ts},
                "$inc": {"event_count": 1},
                "$addToSet": {"pages": doc.get("page")},  # This auto-creates array if needed
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if session_doc and session_doc.get("_id") is not None:
            doc["session_oid"] = session_doc["_id"]
    except Exception as e:
        print(f"[ingest] Warning: Failed to update session {doc.get('session_id')}: {e}")
        pass

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

    # Session upsert already handled above

    return res.inserted_id
