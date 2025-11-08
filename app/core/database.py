"""
MongoDB Database Manager
Provides centralized database connection and collection access
"""
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from app.core.config import MongoConfig

class DatabaseManager:
    """Centralized database connection management"""
    
    def __init__(self):
        self.config = MongoConfig()
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    @property
    def client(self) -> MongoClient:
        """Get MongoDB client with connection pooling"""
        if self._client is None:
            self._client = MongoClient(**self.config.get_connection_settings())
        return self._client

    @property 
    def db(self) -> Database:
        """Get database instance"""
        if self._db is None:
            self._db = self.client[self.config.DB]
        return self._db

    def get_collection(self, name: str) -> Collection:
        """Get collection by name from config"""
        collection_name = self.config.COLLECTIONS.get(name)
        if not collection_name:
            raise ValueError(f"Collection {name} not found in config")
        return self.db[collection_name]

    def close(self):
        """Close database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

# Global database manager instance
db_manager = DatabaseManager()