from fastapi import APIRouter, Header
from typing import Optional
from datetime import datetime
import pytz
from app.services.auth import get_user_by_token
from app.core.db_sync import api_keys_col
from api_key_manager import create_runtime_key

router = APIRouter(tags=["openrouter"])  # Prefix set in main.py

@router.get("/openrouter/key")
def get_key(Authorization: Optional[str] = Header(default=None)):
    if not Authorization:
        return {"error": "unauthenticated"}
    user = get_user_by_token(Authorization)
    if not user:
        return {"error": "unauthenticated"}
    doc = api_keys_col().find_one({"user_id": user["_id"], "provider": "openrouter"})
    if not doc:
        return {"exists": False, "provider": "openrouter"}
    key = doc.get("key_encrypted", "")
    masked = ("*" * max(0, len(key) - 4)) + key[-4:] if key else ""
    return {
        "exists": True,
        "provider": "openrouter",
        "masked_key": masked,
        "updated_at": doc.get("updated_at") and doc["updated_at"].isoformat()
    }

@router.post("/openrouter/key")
def save_key(payload: dict, Authorization: Optional[str] = Header(default=None)):
    if not Authorization:
        return {"error": "unauthenticated"}
    user = get_user_by_token(Authorization)
    if not user:
        return {"error": "unauthenticated"}
    api_key = (payload or {}).get("api_key")
    if not api_key:
        return {"error": "api_key required"}
    if not str(api_key).startswith("sk-or-"):
        return {"error": "Invalid API key format. OpenRouter keys should start with 'sk-or-'"}
    now = datetime.now(pytz.UTC)
    api_keys_col().update_one(
        {"user_id": user["_id"], "provider": "openrouter"},
        {"$set": {"key_encrypted": api_key, "updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True
    )
    return {"status": "ok", "message": "API key saved successfully"}

@router.delete("/openrouter/key")
def delete_key(Authorization: Optional[str] = Header(default=None)):
    if not Authorization:
        return {"error": "unauthenticated"}
    user = get_user_by_token(Authorization)
    if not user:
        return {"error": "unauthenticated"}
    result = api_keys_col().delete_one({"user_id": user["_id"], "provider": "openrouter"})
    if result.deleted_count > 0:
        return {"status": "ok", "message": "API key deleted successfully"}
    return {"error": "No API key found to delete"}

@router.post("/openrouter/provision")
def provision_key(payload: dict, Authorization: Optional[str] = Header(default=None)):
    if not Authorization:
        return {"error": "unauthenticated"}
    user = get_user_by_token(Authorization)
    if not user:
        return {"error": "unauthenticated"}
    name = (payload or {}).get("name") or f"runtime-{str(user.get('_id'))[:6]}"
    limit = (payload or {}).get("limit")
    new_key, meta = create_runtime_key(name=name, limit=limit)
    now = datetime.now(pytz.UTC)
    api_keys_col().update_one(
        {"user_id": user["_id"], "provider": "openrouter"},
        {"$set": {"key_encrypted": new_key, "updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True
    )
    return {"status": "ok", "meta": meta, "message": "Runtime key provisioned successfully"}
