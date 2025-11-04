"""
Database Connection Manager
Provides optimized MongoDB connections with connection pooling and error handling
"""
from typing import Optional
from functools import lru_cache
import logging
import os
from pymongo import MongoClient, collection
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Configuration
class MongoConfig:
    URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DB = os.environ.get("MONGO_DB", "clickstream")
    
    # Connection pool settings
    MAX_POOL_SIZE = int(os.environ.get("MONGO_MAX_POOL_SIZE", "100"))
    MIN_POOL_SIZE = int(os.environ.get("MONGO_MIN_POOL_SIZE", "10"))
    MAX_IDLE_TIME_MS = int(os.environ.get("MONGO_MAX_IDLE_TIME_MS", "60000"))
    
    # Collection names
    COLLECTIONS = {
        "users": "users",
        "events": "events",
        "analyses": "analyses",
        "sessions": "sessions",
        "api_keys": "api_keys",
        "products": "products",
        "carts": "carts"
    }

class DatabaseManager:
    _instance = None
    _client: Optional[MongoClient] = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._client:
            self._connect()
    
    def _connect(self):
        """Establish MongoDB connection with optimized settings"""
        try:
            self._client = MongoClient(
                MongoConfig.URI,
                maxPoolSize=MongoConfig.MAX_POOL_SIZE,
                minPoolSize=MongoConfig.MIN_POOL_SIZE,
                maxIdleTimeMS=MongoConfig.MAX_IDLE_TIME_MS,
                connect=True,  # Ensure connection is established immediately
                serverSelectionTimeoutMS=5000,  # Fail fast if server unreachable
                retryWrites=True,  # Enable automatic retries for write operations
                w="majority"  # Ensure write durability
            )
            self._db = self._client[MongoConfig.DB]
            logger.info("Successfully connected to MongoDB")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
        except PyMongoError as e:
            logger.error(f"MongoDB error occurred: {str(e)}")
            raise
    
    @property
    def db(self):
        """Get database instance with reconnection handling"""
        if not self._client:
            self._connect()
        return self._db
    
    def get_collection(self, name: str) -> collection.Collection:
        """Get collection with validation"""
        if name not in MongoConfig.COLLECTIONS.values():
            raise ValueError(f"Invalid collection name: {name}")
        return self.db[name]
    
    def close(self):
        """Properly close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Closed MongoDB connection")

# Global database manager instance
_db_manager = DatabaseManager()

def get_db():
    """Get the database instance"""
    return _db_manager.db

# Collection accessor functions with caching
@lru_cache(maxsize=1)
def users_col() -> collection.Collection:
    return _db_manager.get_collection(MongoConfig.COLLECTIONS["users"])

@lru_cache(maxsize=1)
def events_col() -> collection.Collection:
    return _db_manager.get_collection(MongoConfig.COLLECTIONS["events"])

@lru_cache(maxsize=1)
def analyses_col() -> collection.Collection:
    return _db_manager.get_collection(MongoConfig.COLLECTIONS["analyses"])

@lru_cache(maxsize=1)
def sessions_col() -> collection.Collection:
    return _db_manager.get_collection(MongoConfig.COLLECTIONS["sessions"])

@lru_cache(maxsize=1)
def api_keys_col() -> collection.Collection:
    return _db_manager.get_collection(MongoConfig.COLLECTIONS["api_keys"])

@lru_cache(maxsize=1)
def products_col() -> collection.Collection:
    return _db_manager.get_collection(MongoConfig.COLLECTIONS["products"])

@lru_cache(maxsize=1)
def carts_col() -> collection.Collection:
    return _db_manager.get_collection(MongoConfig.COLLECTIONS["carts"])
