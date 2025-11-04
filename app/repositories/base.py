"""
Base Repository Pattern Implementation
"""
from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime
from pymongo.collection import Collection
from bson import ObjectId

from app.core.config import Settings
from app.core.db_sync import get_db

# Generic type for models
ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations
    """
    
    def __init__(self, collection_name: str):
        self.db = get_db()
        self.collection: Collection = self.db[collection_name]
        self.settings = Settings()
    
    async def find_one(self, query: Dict) -> Optional[ModelType]:
        """Find single document by query"""
        try:
            return self.collection.find_one(query)
        except Exception as e:
            raise Exception(f"Error in find_one: {str(e)}")
    
    async def find_many(
        self,
        query: Dict,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[List[tuple]] = None
    ) -> List[ModelType]:
        """Find multiple documents by query"""
        try:
            cursor = self.collection.find(query).skip(skip).limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            return list(cursor)
        except Exception as e:
            raise Exception(f"Error in find_many: {str(e)}")
    
    async def create(self, data: Dict) -> ModelType:
        """Create new document"""
        try:
            data["created_at"] = datetime.utcnow()
            data["updated_at"] = datetime.utcnow()
            result = self.collection.insert_one(data)
            return await self.find_one({"_id": result.inserted_id})
        except Exception as e:
            raise Exception(f"Error in create: {str(e)}")
    
    async def update(self, id: str, data: Dict) -> Optional[ModelType]:
        """Update document by ID"""
        try:
            data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": data}
            )
            if result.modified_count:
                return await self.find_one({"_id": ObjectId(id)})
            return None
        except Exception as e:
            raise Exception(f"Error in update: {str(e)}")
    
    async def delete(self, id: str) -> bool:
        """Delete document by ID"""
        try:
            result = self.collection.delete_one({"_id": ObjectId(id)})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Error in delete: {str(e)}")
    
    async def count(self, query: Dict) -> int:
        """Count documents matching query"""
        try:
            return self.collection.count_documents(query)
        except Exception as e:
            raise Exception(f"Error in count: {str(e)}")
    
    async def aggregate(self, pipeline: List[Dict]) -> List[Dict]:
        """Execute aggregation pipeline"""
        try:
            return list(self.collection.aggregate(pipeline))
        except Exception as e:
            raise Exception(f"Error in aggregate: {str(e)}")
    
    async def bulk_write(self, operations: List[Dict]) -> Dict[str, Any]:
        """Execute bulk write operations"""
        try:
            result = self.collection.bulk_write(operations)
            return {
                "inserted": result.inserted_count,
                "modified": result.modified_count,
                "deleted": result.deleted_count
            }
        except Exception as e:
            raise Exception(f"Error in bulk_write: {str(e)}")
    
    async def create_index(self, keys: List[tuple], **kwargs) -> str:
        """Create index on collection"""
        try:
            return self.collection.create_index(keys, **kwargs)
        except Exception as e:
            raise Exception(f"Error creating index: {str(e)}")
    
    async def ensure_indexes(self, indexes: List[Dict]) -> None:
        """Ensure all required indexes exist"""
        try:
            for index in indexes:
                keys = index.pop("keys")
                self.collection.create_index(keys, **index)
        except Exception as e:
            raise Exception(f"Error ensuring indexes: {str(e)}")
            
    async def distinct(self, field: str, query: Optional[Dict] = None) -> List:
        """Get distinct values for a field"""
        try:
            return self.collection.distinct(field, query or {})
        except Exception as e:
            raise Exception(f"Error in distinct: {str(e)}")