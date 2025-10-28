"""
Database connection and configuration
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

from app.core.config import settings

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    async def connect_db(self):
        """
        Connect to MongoDB
        """
        if self.client is None:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.MONGODB_DB]

    async def close_db(self):
        """
        Close MongoDB connection
        """
        if self.client is not None:
            self.client.close()
            self.client = None

    async def get_db(self):
        """
        Get database instance
        """
        if self.db is None:
            await self.connect_db()
        return self.db

# Global database instance
database = Database()

async def get_database():
    """
    Get database instance for dependency injection
    """
    if database.db is None:
        await database.connect_db()
    return database.db