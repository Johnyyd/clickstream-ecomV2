"""
Data Ingestion Module
Handles event ingestion with validation, processing and storage optimization.
Supports both batch and streaming ingestion with Kafka integration.
"""

import logging
import json as _json
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from functools import lru_cache
import pytz
from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from kafka import KafkaProducer
from db import events_col, sessions_col, products_col, users_col

__all__ = ["ingest_event", "EventProcessor", "EventStorage"]

# Constants
_KAFKA_TOPIC = "clickstream_events"
_KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
_KAFKA_CLIENT_ID = "clickstream_ingestion"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka setup
@lru_cache(maxsize=1)
def _get_kafka_producer() -> KafkaProducer:
    """Get cached Kafka producer instance
    
    Returns:
        KafkaProducer: Configured Kafka producer for event streaming
        
    Raises:
        Exception: If producer creation fails
    """
    try:
        return KafkaProducer(
            bootstrap_servers=_KAFKA_BOOTSTRAP_SERVERS,
            client_id=_KAFKA_CLIENT_ID,
            value_serializer=lambda v: _json.dumps(v).encode("utf-8"),
            acks='all',
            retries=3
        )
    except Exception as e:
        logger.error(f"Failed to create Kafka producer: {str(e)}")
        raise

# Kafka Configuration
class KafkaConfig:
    BROKERS = os.getenv("KAFKA_BROKERS")
    TOPIC = os.getenv("KAFKA_TOPIC", "clickstream.events")
    BATCH_SIZE = int(os.getenv("KAFKA_BATCH_SIZE", "100"))
    LINGER_MS = int(os.getenv("KAFKA_LINGER_MS", "100"))
    COMPRESSION = os.getenv("KAFKA_COMPRESSION", "snappy")

# Kafka singleton producer
_kafka_producer = None

@lru_cache(maxsize=1)
def get_kafka_producer():
    """Get or create Kafka producer with optimized settings"""
    global _kafka_producer
    if not KafkaConfig.BROKERS:
        return None
        
    if _kafka_producer is None:
        try:
            from kafka import KafkaProducer
            _kafka_producer = KafkaProducer(
                bootstrap_servers=KafkaConfig.BROKERS.split(","),
                value_serializer=lambda v: _json.dumps(v).encode("utf-8"),
                compression_type=KafkaConfig.COMPRESSION,
                batch_size=KafkaConfig.BATCH_SIZE,
                linger_ms=KafkaConfig.LINGER_MS,
                acks="all",
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            logger.info("Successfully created Kafka producer")
        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {str(e)}")
            _kafka_producer = None
    return _kafka_producer

class EventValidator:
    """Validates incoming event data"""
    
    REQUIRED_FIELDS = {
        "user_id": str,
        "session_id": str,
        "event_type": str,
        "page": str,
        "timestamp": (int, float),
        "properties": dict
    }
    
    VALID_EVENT_TYPES = {
        "pageview",
        "search",
        "product_view",
        "add_to_cart",
        "remove_from_cart",
        "purchase",
        "login",
        "signup",
        "logout"
    }
    
    @classmethod
    def validate(cls, event: Dict) -> tuple[bool, Optional[str]]:
        """Validate event data structure and content"""
        try:
            # Check required fields and types
            for field, field_type in cls.REQUIRED_FIELDS.items():
                if field not in event:
                    return False, f"Missing required field: {field}"
                if not isinstance(event[field], field_type):
                    return False, f"Invalid type for {field}: expected {field_type}"
            
            # Validate event_type
            if event["event_type"] not in cls.VALID_EVENT_TYPES:
                return False, f"Invalid event_type: {event['event_type']}"
            
            # Validate timestamp
            if event["timestamp"] <= 0:
                return False, "Invalid timestamp"
                
            # Validate page format
            if not event["page"].startswith("/"):
                return False, "Page must start with /"
                
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

class SessionManager:
    """Manages user session tracking and updates"""
    
    def __init__(self):
        self._session_cache = {}
    
    def update_session(self, event: Dict) -> str:
        """Update session information for an event"""
        try:
            session_id = event["session_id"]
            user_id = event["user_id"]
            timestamp = datetime.fromtimestamp(event["timestamp"], tz=pytz.UTC)
            
            # Update in MongoDB with optimized query
            result = sessions_col().find_one_and_update(
                {"session_id": session_id},
                {
                    "$setOnInsert": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "created_at": timestamp
                    },
                    "$min": {"first_event_at": timestamp},
                    "$max": {"last_event_at": timestamp},
                    "$inc": {"event_count": 1},
                    "$addToSet": {"pages": event["page"]},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                upsert=True,
                return_document=ReturnDocument.AFTER
            )
            
            # Update cache
            if result:
                self._session_cache[session_id] = {
                    "user_id": result["user_id"],
                    "first_event_at": result["first_event_at"],
                    "last_event_at": result["last_event_at"],
                    "event_count": result["event_count"],
                    "pages": set(result["pages"])
                }
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise

class EventProcessor:
    """Processes and enriches events before storage"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.validator = EventValidator
    
    def process_event(self, event: Dict) -> Dict:
        """Process and enrich event data"""
        try:
            # Validate
            is_valid, error = self.validator.validate(event)
            if not is_valid:
                raise ValueError(error)
            
            # Add processing metadata
            processed = event.copy()
            processed.update({
                "processed_at": datetime.utcnow(),
                "ingestion_id": str(ObjectId())
            })
            
            # Enrich with context
            if "product_id" in event.get("properties", {}):
                self._enrich_product_data(processed)
            self._enrich_user_data(processed)
            
            # Update session
            self.session_manager.update_session(processed)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            raise
    
    def _enrich_product_data(self, event: Dict) -> None:
        """Add product details to event"""
        try:
            product_id = event["properties"]["product_id"]
            product = products_col().find_one({"_id": ObjectId(product_id)})
            if product:
                event["properties"]["product_details"] = {
                    "name": product.get("name"),
                    "category": product.get("category"),
                    "price": product.get("price")
                }
        except Exception as e:
            logger.warning(f"Error enriching product data: {str(e)}")
    
    def _enrich_user_data(self, event: Dict) -> None:
        """Add user details to event"""
        try:
            user = users_col().find_one({"_id": ObjectId(event["user_id"])})
            if user:
                event["properties"]["user_details"] = {
                    "username": user.get("username"),
                    "user_type": user.get("user_type", "standard")
                }
        except Exception as e:
            logger.warning(f"Error enriching user data: {str(e)}")

class EventStorage:
    """Handles efficient event storage with batching"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.current_batch: List[Dict] = []
    
    def store_event(self, event: Dict) -> None:
        """Store single event with batching"""
        try:
            self.current_batch.append(event)
            
            if len(self.current_batch) >= self.batch_size:
                self.flush()
                
        except Exception as e:
            logger.error(f"Error storing event: {str(e)}")
            raise
    
    def flush(self) -> None:
        """Flush current batch to database"""
        if not self.current_batch:
            return
            
        try:
            events_col().insert_many(self.current_batch)
            self.current_batch.clear()
            
        except Exception as e:
            logger.error(f"Error flushing events: {str(e)}")
            raise

# Global instances
_processor = EventProcessor()
_storage = EventStorage()

def ingest_event(event_json: Dict) -> Dict[str, Any]:
    """
    Main entry point for event ingestion and processing pipeline.
    Handles validation, enrichment, storage and streaming of events.
    
    The function orchestrates the complete event processing flow:
    1. Validates event data format and required fields
    2. Enriches with additional context (user, product info)
    3. Manages user sessions
    4. Stores to MongoDB for analytics
    5. Streams to Kafka for real-time processing
    
    Args:
        event_json: Raw event data dictionary with required fields:
            - timestamp: Unix epoch (optional, defaults to current time)
            - event_type: Type of event (e.g. "pageview", "purchase")
            - page: Current page path
            - user_id: User identifier (optional)
            - properties: Additional event properties dict
            
    Returns:
        Dict containing:
            - status: "success" if processed successfully
            - event_id: MongoDB ObjectId of stored event
            - processed_at: ISO timestamp of processing
            - session_id: ID of the associated session
            - enriched_fields: List of fields that were enriched
            
    Raises:
        HTTPException (400): If event validation fails
        HTTPException (500): If processing/storage fails
        
    Example event:
    {
        "event_type": "pageview",
        "page": "/products/123", 
        "timestamp": 1672531200,
        "properties": {
            "referrer": "/category/456",
            "product_id": "789"
        },
        "user_id": "user_123",
        "session_id": "sess_456" 
    }
    """
    try:
        # Process event
        processed_event = _processor.process_event(event_json)
        
        # Store in database
        _storage.store_event(processed_event)
        
        # Send to Kafka
        producer = _get_kafka_producer()
        payload = {
            "event": processed_event,
            "metadata": {
                "ingested_at": datetime.utcnow().isoformat(),
                "version": "2.0"
            }
        }
        producer.send(_KAFKA_TOPIC, payload)
        
        result = {
            "status": "success",
            "event_id": str(processed_event["_id"]),
            "processed_at": processed_event["processed_at"].isoformat(),
            "session_id": processed_event.get("session_id"),
            "enriched_fields": list(processed_event.get("properties", {}).keys())
        }
        
        logger.info(f"Successfully processed event {result['event_id']}")
        return result
        
    except ValueError as ve:
        logger.warning(f"Event validation failed: {str(ve)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event data: {str(ve)}"
        )
        
    except Exception as e:
        logger.error(f"Event ingestion failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest event: {str(e)}"
        )

