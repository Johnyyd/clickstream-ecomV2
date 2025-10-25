from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Event(BaseModel):
    page: Optional[str] = None
    event_type: str = Field(default="pageview")
    properties: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[float] = None  # epoch seconds from client

class EventIngestResponse(BaseModel):
    event_id: str

class EventBatch(BaseModel):
    events: List[Event]

class EventBatchResponse(BaseModel):
    inserted: int
    ids: List[str]
