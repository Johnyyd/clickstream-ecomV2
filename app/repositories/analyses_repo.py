from typing import Optional, Dict, Any, List
from bson import ObjectId
from app.core.db_sync import analyses_col


class AnalysesRepository:
    def __init__(self):
        self.col = analyses_col()

    def get_by_id(self, aid: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(aid)
        except Exception:
            return None
        doc = self.col.find_one({"_id": oid})
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])  # normalize for JSON
        return doc

    def list_by_user(self, user_id: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if user_id:
            try:
                query["user_id"] = ObjectId(user_id)
            except Exception:
                # if not a valid ObjectId, fallback to raw value
                query["user_id"] = user_id
        cur = (
            self.col.find(query)
            .sort("created_at", -1)
            .skip(int(offset))
            .limit(int(limit))
        )
        items: List[Dict[str, Any]] = []
        for d in cur:
            d["_id"] = str(d["_id"])  # normalize
            if isinstance(d.get("user_id"), ObjectId):
                d["user_id"] = str(d["user_id"])
            items.append(d)
        return items

    def insert(self, doc: Dict[str, Any]) -> str:
        res = self.col.insert_one(doc)
        return str(res.inserted_id)
