from fastapi import APIRouter, Header
from typing import Optional, List, Dict, Any
from bson import ObjectId
from auth import get_user_by_token
from db import users_col, analyses_col, products_col

router = APIRouter(prefix="/api", tags=["recommendations"])

@router.get("/recommendations")
def get_recommendations(Authorization: Optional[str] = Header(default=None)):
    if not Authorization:
        return {"error": "unauthenticated"}
    user = get_user_by_token(Authorization)
    if not user:
        return {"error": "unauthenticated"}

    try:
        last = analyses_col().find({
            "user_id": user["_id"],
            "product_recommendations": {"$exists": True, "$ne": []}
        }).sort("created_at", -1).limit(1)
        last = list(last)
        items: List[Dict[str, Any]] = []
        if last:
            items = last[0].get("product_recommendations", [])
        if not items:
            udoc = users_col().find_one({"_id": user["_id"]}, {"product_recommendations": 1}) or {}
            history = udoc.get("product_recommendations", [])
            if history:
                items = (history[-1] or {}).get("items", [])

        ids = [i.get("product_id") for i in items if i.get("product_id")]
        prod_map: Dict[str, Any] = {}
        if ids:
            obj_ids = []
            for pid in ids:
                try:
                    obj_ids.append(ObjectId(str(pid)))
                except Exception:
                    pass
            if obj_ids:
                for p in products_col().find({"_id": {"$in": obj_ids}}):
                    prod_map[str(p["_id"])] = {
                        "name": p.get("name"),
                        "category": p.get("category"),
                        "price": p.get("price"),
                        "tags": p.get("tags", [])
                    }
        result_items = []
        for i in items:
            pid = str(i.get("product_id"))
            enriched = {
                "product_id": pid,
                "name": i.get("name") or (prod_map.get(pid) or {}).get("name"),
                "category": i.get("category") or (prod_map.get(pid) or {}).get("category"),
                "price": i.get("price") or (prod_map.get(pid) or {}).get("price"),
                "tags": i.get("tags") or (prod_map.get(pid) or {}).get("tags", []),
                "reason": i.get("reason", "")
            }
            result_items.append(enriched)
        return {"items": result_items}
    except Exception as e:
        return {"error": str(e)}
