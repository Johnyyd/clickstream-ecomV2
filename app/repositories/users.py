"""
User repository for MongoDB operations
"""
from typing import Optional
from datetime import datetime
from bson import ObjectId

from app.core.security import get_password_hash

class UserRepository:
    def __init__(self, db):
        self.db = db
        self.collection = db.users

    async def create(self, username: str, password: str, email: Optional[str] = None) -> dict:
        """Create new user"""
        user = {
            "username": username,
            "hashed_password": get_password_hash(password),
            "email": email,
            "is_active": True,
            "is_admin": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await self.collection.insert_one(user)
        user["id"] = str(result.inserted_id)
        return user

    async def get(self, user_id: str) -> Optional[dict]:
        """Get user by ID"""
        try:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["id"] = str(user.pop("_id"))
            return user
        except:
            return None

    async def get_by_username(self, username: str) -> Optional[dict]:
        """Get user by username"""
        user = await self.collection.find_one({"username": username})
        if user:
            user["id"] = str(user.pop("_id"))
        return user

    async def get_by_email(self, email: str) -> Optional[dict]:
        """Get user by email"""
        user = await self.collection.find_one({"email": email})
        if user:
            user["id"] = str(user.pop("_id"))
        return user

    async def update(self, user_id: str, update_data: dict) -> Optional[dict]:
        """Update user"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            # Hash password if provided
            if "password" in update_data:
                update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
                
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result["id"] = str(result.pop("_id"))
            return result
        except:
            return None

    async def delete(self, user_id: str) -> bool:
        """Delete user"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except:
            return False