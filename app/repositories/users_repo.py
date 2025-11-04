from typing import Optional, Dict, Any, List
from bson import ObjectId
from app.core.db_sync import users_col

class UsersRepository:
    def __init__(self):
        self.col = users_col()

    def get_by_id(self, uid: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(uid)
        except Exception:
            return None
        doc = self.col.find_one({"_id": oid})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])  # normalize for JSON
        return doc

    def get_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        doc = self.col.find_one({"token": token})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])  # normalize for JSON
        return doc

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        if not username:
            return None
        doc = self.col.find_one({"username": username})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])  # normalize
        return doc
    
    def create(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        result = self.col.insert_one(user)
        user["_id"] = str(result.inserted_id)
        return user

    def upsert_user(self, user: Dict[str, Any]) -> str:
        # Expects user to contain a unique field (username or email)
        key = {}
        if user.get("username"):
            key = {"username": user["username"]}
        elif user.get("email"):
            key = {"email": user["email"]}
        else:
            raise ValueError("user must include username or email for upsert")
        res = self.col.find_one_and_update(
            key,
            {"$set": user},
            upsert=True,
            return_document=True,
        )
        if res and isinstance(res.get("_id"), ObjectId):
            return str(res["_id"])
        # If driver didn't return the document, fetch it
        doc = self.col.find_one(key)
        return str(doc["_id"]) if doc else ""

    def add_recommendations_history(self, user_id: str, product_ids: List[str]) -> bool:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return False
        self.col.update_one(
            {"_id": oid},
            {"$push": {"recommendations_history": {"$each": product_ids}}},
            upsert=False,
        )
        return True
