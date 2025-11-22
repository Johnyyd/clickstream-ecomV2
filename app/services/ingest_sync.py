from __future__ import annotations
"""
Synchronous Event Ingestion Service (legacy-compatible)
Mirrors root-level ingest.py functionality to enable gradual migration.
"""
import logging
import json as _json
import os
import pytz
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from functools import lru_cache
from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from app.core.db_sync import events_col, sessions_col, products_col, users_col, orders_col, carts_col

if TYPE_CHECKING:
    # Only imported for type hints; avoids runtime dependency
    from kafka import KafkaProducer  # type: ignore

logger = logging.getLogger(__name__)

_KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "clickstream.events")
_KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
_KAFKA_CLIENT_ID = "clickstream_ingestion"
_KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "1") == "1"
_KAFKA_OPTIONAL = os.getenv("KAFKA_OPTIONAL", "1") == "1"

@lru_cache(maxsize=1)
def _get_kafka_producer() -> Optional[KafkaProducer]:
    if not _KAFKA_ENABLED:
        # Quiet kafka library logs when disabled
        try:
            logging.getLogger("kafka").setLevel(logging.WARNING)
        except Exception:
            pass
        logger.info("Kafka disabled via KAFKA_ENABLED=0; skipping producer creation")
        return None
    try:
        # Import lazily to avoid import cost/errors when disabled
        from kafka import KafkaProducer  # type: ignore
        return KafkaProducer(
            bootstrap_servers=_KAFKA_BOOTSTRAP_SERVERS,
            client_id=_KAFKA_CLIENT_ID,
            value_serializer=lambda v: _json.dumps(v).encode("utf-8"),
            acks='all',
            retries=3
        )
    except Exception as e:
        if _KAFKA_OPTIONAL:
            try:
                logging.getLogger("kafka").setLevel(logging.WARNING)
            except Exception:
                pass
            logger.warning(f"Kafka optional: producer creation failed and will be skipped: {str(e)}")
            return None
        logger.error(f"Failed to create Kafka producer (KAFKA_OPTIONAL=0): {str(e)}")
        raise

class EventValidator:
    REQUIRED_FIELDS = {
        "user_id": str,
        "session_id": str,
        "event_type": str,
        "page": str,
        "timestamp": (int, float),
        "properties": dict
    }
    VALID_EVENT_TYPES = {
        "pageview","search","product_view","add_to_cart","remove_from_cart",
        "checkout","purchase","login","signup","logout"
    }

    @classmethod
    def validate(cls, event: Dict) -> tuple[bool, Optional[str]]:
        try:
            for field, field_type in cls.REQUIRED_FIELDS.items():
                if field not in event:
                    return False, f"Missing required field: {field}"
                if not isinstance(event[field], field_type):
                    return False, f"Invalid type for {field}: expected {field_type}"
            if event["event_type"] not in cls.VALID_EVENT_TYPES:
                return False, f"Invalid event_type: {event['event_type']}"
            if event["timestamp"] <= 0:
                return False, "Invalid timestamp"
            if not event["page"].startswith("/"):
                return False, "Page must start with /"
            return True, None
        except Exception as e:
            return False, f"Validation error: {str(e)}"

class SessionManager:
    def update_session(self, event: Dict) -> str:
        try:
            session_id = event["session_id"]
            timestamp = datetime.fromtimestamp(event["timestamp"])
            # Normalize user_id to ObjectId when possible so sessions.user_id
            # matches the users collection _id type
            user_id_value = event.get("user_id")
            user_oid: Optional[ObjectId]
            try:
                user_oid = ObjectId(user_id_value) if user_id_value else None
            except Exception:
                user_oid = None
            # Build update document; if we have a valid ObjectId user, also set it (not only on insert)
            update_doc: Dict[str, Any] = {
                "$setOnInsert": {
                    "session_id": session_id,
                    "created_at": timestamp
                },
                "$min": {"first_event_at": timestamp},
                "$max": {"last_event_at": timestamp},
                "$inc": {"event_count": 1},
                "$addToSet": {"pages": event["page"]},
                "$set": {"updated_at": datetime.utcnow()},
            }
            # Always set user_id from the current event. If it's a valid ObjectId, store the ObjectId;
            # otherwise keep the raw value (e.g., guest UUID). Using only $set avoids conflicts with $setOnInsert.
            update_doc["$set"].update({
                "user_id": user_oid if user_oid is not None else event.get("user_id")
            })

            result = sessions_col().find_one_and_update(
                {"session_id": session_id},
                update_doc,
                upsert=True,
                return_document=ReturnDocument.AFTER
            )
            return session_id
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise

class EventProcessor:
    def __init__(self):
        self.session_manager = SessionManager()
        self.validator = EventValidator

    def process_event(self, event: Dict) -> Dict:
        is_valid, error = self.validator.validate(event)
        if not is_valid:
            raise ValueError(error)
        processed = event.copy()
        processed.update({
            "processed_at": datetime.now(timezone.utc),
            "_id": ObjectId(),  # ensure ID exists before batch insert
        })
        # Add ISODate for dashboards while keeping numeric epoch for Spark
        try:
            ts = int(event.get("timestamp", 0))
            if ts > 0:
                occurred_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                processed["occurred_at"] = occurred_dt
                processed["occurred_at_iso"] = occurred_dt.isoformat(timespec="milliseconds")
        except Exception:
            pass
        if "product_id" in event.get("properties", {}):
            try:
                product = products_col().find_one({"_id": ObjectId(event["properties"]["product_id"])})
                if product:
                    processed["properties"]["product_details"] = {
                        "name": product.get("name"),
                        "category": product.get("category"),
                        "price": product.get("price"),
                    }
            except Exception:
                pass
        try:
            user = users_col().find_one({"_id": ObjectId(event["user_id"])})
            if user:
                processed["properties"].setdefault("user_details", {})
                processed["properties"]["user_details"].update({
                    "username": user.get("username"),
                    "user_type": user.get("user_type", "standard"),
                })
        except Exception:
            pass
        self.session_manager.update_session(processed)
        return processed

class EventStorage:
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.current_batch: List[Dict] = []
    def store_event(self, event: Dict) -> None:
        """Persist a single event immediately.

        For the analytics demo / low-volume environments, it's more important that
        each event is visible in MongoDB right away than to batch aggressively.
        We therefore insert each event individually instead of buffering in
        memory and waiting until batch_size is reached.
        """
        try:
            events_col().insert_one(event)
        except Exception as e:
            logger.error(f"Failed to store event: {str(e)}")
            raise
    def flush(self) -> None:
        if not self.current_batch:
            return
        events_col().insert_many(self.current_batch)
        self.current_batch.clear()

_processor = EventProcessor()
_storage = EventStorage()

def ingest_event(event_json: Dict) -> Dict[str, Any]:
    try:
        processed_event = _processor.process_event(event_json)
        _storage.store_event(processed_event)
        # If this is a purchase event from the shop, also persist a corresponding order document
        try:
            if str(processed_event.get("event_type")) == "purchase":
                props = processed_event.get("properties") or {}
                total = props.get("total_amount")
                try:
                    total = float(total) if total is not None else None
                except Exception:
                    total = None
                created_at = processed_event.get("occurred_at") or processed_event.get("processed_at")
                # user_id: store as string of ObjectId when possible (align with seeded orders)
                uid_raw = processed_event.get("user_id")
                try:
                    uid_str = str(ObjectId(uid_raw))
                except Exception:
                    uid_str = str(uid_raw) if uid_raw is not None else None
                order_doc: Dict[str, Any] = {
                    "user_id": uid_str,
                    "session_id": processed_event.get("session_id"),
                    "total": total,
                    "created_at": created_at,
                    "source": "shop",
                    "event_id": processed_event.get("_id"),
                }
                try:
                    orders_col().insert_one(order_doc)
                except Exception:
                    logger.warning("Order insert failed; continuing ingest pipeline", exc_info=True)
                try:
                    uid_obj = None
                    try:
                        uid_obj = ObjectId(uid_raw) if uid_raw else None
                    except Exception:
                        uid_obj = None
                    if uid_obj is not None:
                        carts_col().update_one({"user_id": uid_obj}, {"$set": {"items": []}}, upsert=True)
                except Exception:
                    logger.warning("Cart clear failed after purchase; continuing ingest pipeline", exc_info=True)
        except Exception:
            logger.warning("Order side-effect failed; continuing ingest pipeline", exc_info=True)
        # Maintain legacy nested payload structure: {event, metadata}
        producer = _get_kafka_producer()
        payload = {
            "event": processed_event,
            "metadata": {
                "ingested_at": datetime.utcnow().isoformat(),
                "version": "2.0"
            }
        }
        if producer is not None:
            try:
                producer.send(_KAFKA_TOPIC, payload)
            except Exception as e:
                if not _KAFKA_OPTIONAL:
                    raise
                logger.warning(f"Kafka optional: send failed and was skipped: {str(e)}")
        return {
            "status": "success",
            "event_id": str(processed_event["_id"]),
            "processed_at": processed_event["processed_at"].isoformat(),
            "session_id": processed_event.get("session_id"),
            "enriched_fields": list(processed_event.get("properties", {}).keys()),
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid event data: {str(ve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest event: {str(e)}")
