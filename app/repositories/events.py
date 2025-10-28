"""
Event repository for MongoDB operations
"""
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

class EventRepository:
    def __init__(self, db):
        self.db = db
        self.collection = db.events

    async def insert_one(self, event_data: dict) -> ObjectId:
        """Insert single event"""
        result = await self.collection.insert_one(event_data)
        return result.inserted_id

    async def insert_many(self, events: List[dict]) -> List[ObjectId]:
        """Insert multiple events"""
        result = await self.collection.insert_many(events)
        return result.inserted_ids

    async def get_session_events(self, session_id: str) -> List[dict]:
        """Get all events for a session"""
        cursor = self.collection.find({"session_id": session_id})
        return await cursor.to_list(None)

    async def get_user_events(self, user_id: str, limit: int = 1000) -> List[dict]:
        """Get recent events for a user"""
        cursor = self.collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(None)

    async def get_user_sessions(self, user_id: str, limit: int = 100) -> List[dict]:
        """Get unique sessions for a user"""
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$session_id",
                "first_event": {"$first": "$$ROOT"},
                "event_count": {"$sum": 1}
            }},
            {"$sort": {"first_event.timestamp": -1}},
            {"$limit": limit}
        ]
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(None)

    async def get_recent_sessions(self, limit: int = 10) -> List[dict]:
        """Get most recent sessions"""
        pipeline = [
            {"$group": {
                "_id": "$session_id",
                "first_event": {"$first": "$$ROOT"},
                "last_event": {"$last": "$$ROOT"},
                "event_count": {"$sum": 1}
            }},
            {"$sort": {"last_event.timestamp": -1}},
            {"$limit": limit}
        ]
        cursor = self.collection.aggregate(pipeline)
        return await cursor.to_list(None)