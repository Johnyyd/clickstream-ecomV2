from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth import create_user, login_user
from auth import get_user_by_token
from auth import hash_password
from app.repositories.users_repo import UsersRepository
from db import users_col, sessions_col
import os

router = APIRouter(prefix="/api", tags=["auth"])

# Dependency function for protected routes
def get_current_user(Authorization: Optional[str] = Header(default=None)):
    """
    FastAPI dependency to get the current authenticated user.
    Raises HTTPException if not authenticated.
    """
    if not Authorization:
        raise HTTPException(status_code=401, detail="Unauthorized - No token provided")
    user = get_user_by_token(Authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized - Invalid token")
    return {
        "user_id": str(user.get("_id")),
        "username": user.get("username"),
        "role": user.get("role", "user"),
    }

class SignUpBody(BaseModel):
    username: str
    email: str
    password: str

class LoginBody(BaseModel):
    username: str
    password: str

@router.post("/signup")
def signup(body: SignUpBody):
    uid = create_user(body.username, body.email, body.password)
    return {"user_id": str(uid)}

@router.post("/login")
def login(body: LoginBody):
    result, msg = login_user(body.username, body.password)
    if not result:
        return {"error": msg}
    # Create a browsing session tied to this login (ObjectId _id, unique string session_id)
    try:
        from datetime import datetime
        import pytz, time
        user = result["user"]
        uid = str(user["_id"]) if isinstance(user.get("_id"), (str,)) else str(user.get("_id"))
        session_id = f"session_{uid[-6:]}_{int(time.time())}"
        now = datetime.now(pytz.UTC)
        from pymongo import ReturnDocument
        sessions_col().find_one_and_update(
            {"session_id": session_id},
            {
                "$setOnInsert": {
                    "session_id": session_id,
                    "user_id": user.get("_id"),
                    "client_id": None,
                    "created_at": now,
                    "pages": [],
                    "event_count": 0,
                },
                "$max": {"last_event_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except Exception:
        session_id = None
    return {
        "token": result["token"],
        "user_id": str(result["user"]["_id"]),
        "username": result["user"].get("username"),
        "role": result["user"].get("role", "user"),
        "session_id": session_id,
    }

@router.get("/me")
def me(Authorization: Optional[str] = Header(default=None)):
    if not Authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = get_user_by_token(Authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {
        "user_id": str(user.get("_id")),
        "username": user.get("username"),
        "role": user.get("role", "user"),
    }

class CreateAdminBody(BaseModel):
    username: str
    email: str
    password: str

@router.post("/create-admin")
def create_admin(body: CreateAdminBody, Authorization: Optional[str] = Header(default=None), x_admin_setup_key: Optional[str] = Header(default=None)):
    # Allow bootstrap without key if no admin exists yet; otherwise require ADMIN_SETUP_KEY or an existing admin token
    col = users_col()
    has_admin = col.count_documents({"role": "admin"}, limit = 1) > 0
    if has_admin:
        ok = False
        setup_key = os.environ.get("ADMIN_SETUP_KEY") or ""
        if setup_key and x_admin_setup_key and x_admin_setup_key == setup_key:
            ok = True
        else:
            if Authorization:
                me = get_user_by_token(Authorization)
                if me and me.get("role") == "admin":
                    ok = True
        if not ok:
            raise HTTPException(status_code=403, detail="Forbidden")

    repo = UsersRepository()
    existing = repo.find_by_username(body.username)
    if existing:
        update_doc = {"email": body.email, "password_hash": hash_password(body.password), "role": "admin"}
        col.update_one({"username": body.username}, {"$set": update_doc})
        uid = existing.get("_id")
    else:
        uid = repo.upsert_user({
            "username": body.username,
            "email": body.email,
            "password_hash": hash_password(body.password),
            "role": "admin",
        })
    return {"user_id": str(uid), "username": body.username, "role": "admin"}
