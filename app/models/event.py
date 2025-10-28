"""
Event models
"""
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime

class Event(BaseModel):
    session_id: str
    event_type: str
    properties: Dict[str, Any]

class EventBatch(BaseModel):
    events: List[Event]

class EventInDB(Event):
    id: str
    timestamp: datetime
    user_id: str = None

    class Config:
        from_attributes = True