from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from auth import get_user_by_token
from db import carts_col, products_col
from bson import ObjectId

router = APIRouter(prefix="/api", tags=["cart"])

class CartItem(BaseModel):
    product_id: str
    quantity: int

class CartUpdateBody(BaseModel):
    items: List[CartItem]


def _require_user(Authorization: Optional[str]):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = get_user_by_token(Authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def _enrich_items(items: List[Dict[str, Any]]):
    # Attach product info for display
    pids = [str(it.get("product_id")) for it in items if it.get("product_id")]
    if not pids:
        return []
    obj_ids = []
    for pid in pids:
        try:
            obj_ids.append(ObjectId(pid))
        except Exception:
            pass
    prod_map = {}
    for p in products_col().find({"_id": {"$in": obj_ids}}):
        prod_map[str(p["_id"])] = p
    enriched = []
    for it in items:
        pid = str(it.get("product_id"))
        p = prod_map.get(pid)
        if not p:
            # still return basic item
            enriched.append({
                "product_id": pid,
                "quantity": int(it.get("quantity") or 1),
            })
            continue
        enriched.append({
            "product_id": pid,
            "quantity": int(it.get("quantity") or 1),
            "name": p.get("name"),
            "price": p.get("price"),
            "image_url": p.get("image_url"),
            "category": p.get("category"),
        })
    return enriched


@router.get("/cart")
def get_cart(Authorization: Optional[str] = Header(default=None)):
    user = _require_user(Authorization)
    try:
        uid = ObjectId(str(user.get("_id")))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    doc = carts_col().find_one({"user_id": uid})
    items = doc.get("items", []) if doc else []
    return {"items": _enrich_items(items)}


@router.put("/cart")
def put_cart(body: CartUpdateBody, Authorization: Optional[str] = Header(default=None)):
    user = _require_user(Authorization)
    try:
        uid = ObjectId(str(user.get("_id")))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    # normalize quantities
    items = [{"product_id": it.product_id, "quantity": max(1, int(it.quantity))} for it in body.items]
    carts_col().update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "items": items}},
        upsert=True,
    )
    return {"ok": True}


@router.delete("/cart")
def clear_cart(Authorization: Optional[str] = Header(default=None)):
    user = _require_user(Authorization)
    try:
        uid = ObjectId(str(user.get("_id")))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    carts_col().update_one({"user_id": uid}, {"$set": {"items": []}}, upsert=True)
    return {"ok": True}


class CartAddBody(BaseModel):
    product_id: str
    quantity: int = 1


@router.post("/cart/add")
def add_item(body: CartAddBody, Authorization: Optional[str] = Header(default=None)):
    user = _require_user(Authorization)
    try:
        uid = ObjectId(str(user.get("_id")))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    pid = body.product_id
    qty = max(1, int(body.quantity or 1))
    col = carts_col()
    doc = col.find_one({"user_id": uid})
    if not doc:
        col.insert_one({"user_id": uid, "items": [{"product_id": pid, "quantity": qty}]})
        return {"ok": True}
    items = doc.get("items", [])
    for it in items:
        if str(it.get("product_id")) == pid:
            it["quantity"] = max(1, int(it.get("quantity") or 0) + qty)
            break
    else:
        items.append({"product_id": pid, "quantity": qty})
    col.update_one({"_id": doc["_id"]}, {"$set": {"items": items}})
    return {"ok": True}


class CartRemoveBody(BaseModel):
    product_id: str


@router.post("/cart/remove")
def remove_item(body: CartRemoveBody, Authorization: Optional[str] = Header(default=None)):
    user = _require_user(Authorization)
    try:
        uid = ObjectId(str(user.get("_id")))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    pid = body.product_id
    col = carts_col()
    doc = col.find_one({"user_id": uid})
    if not doc:
        return {"ok": True}
    items = [it for it in (doc.get("items", []) or []) if str(it.get("product_id")) != pid]
    col.update_one({"_id": doc["_id"]}, {"$set": {"items": items}})
    return {"ok": True}
