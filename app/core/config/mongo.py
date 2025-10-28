"""
MongoDB Configuration
"""
from typing import Dict, Union
from pydantic import BaseModel, Field

class MongoConfig(BaseModel):
    """MongoDB connection and collection configuration"""
    
    # Connection Settings
    URI: str = Field(
        "mongodb://localhost:27017",
        description="MongoDB connection URI"
    )
    DB: str = Field("clickstream", description="MongoDB database name")
    
    # Pool Settings  
    MIN_POOL_SIZE: int = Field(10, ge=1, description="Minimum connection pool size")
    MAX_POOL_SIZE: int = Field(100, ge=10, description="Maximum connection pool size") 
    MAX_IDLE_TIME_MS: int = Field(
        60000, ge=1000,
        description="Maximum connection idle time (ms)"
    )

    # Collection Names
    COLLECTIONS: Dict[str, str] = Field(
        default={
            "users": "users",
            "events": "events", 
            "analyses": "analyses",
            "sessions": "sessions",
            "api_keys": "api_keys",
            "products": "products",
            "carts": "carts"
        },
        description="MongoDB collection names"
    )

    def get_connection_settings(self) -> Dict[str, Union[str, int]]:
        """Get MongoDB connection settings"""
        return {
            "host": self.URI,
            "minPoolSize": self.MIN_POOL_SIZE, 
            "maxPoolSize": self.MAX_POOL_SIZE,
            "maxIdleTimeMS": self.MAX_IDLE_TIME_MS
        }

    class Config:
        env_prefix = "MONGO_"