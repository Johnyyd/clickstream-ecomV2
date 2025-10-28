"""
Event ingestion service
"""
from typing import List
from datetime import datetime

from app.models.event import Event, EventBatch

async def ingest_event(event: Event, db, current_user=None):
    """
    Ingest single event
    """
    event_data = event.dict()
    event_data["timestamp"] = datetime.utcnow()
    
    if current_user:
        event_data["user_id"] = str(current_user.id)
    
    result = await db.events.insert_one(event_data)
    event_data["event_id"] = str(result.inserted_id)
    
    return event_data

async def ingest_batch(batch: EventBatch, db, current_user=None):
    """
    Ingest batch of events
    """
    events = []
    for event in batch.events:
        event_data = event.dict()
        event_data["timestamp"] = datetime.utcnow()
        
        if current_user:
            event_data["user_id"] = str(current_user.id)
            
        events.append(event_data)
    
    result = await db.events.insert_many(events)
    
    # Add inserted IDs to events
    for event, inserted_id in zip(events, result.inserted_ids):
        event["event_id"] = str(inserted_id)
        
    return events