# auth.py
import os, hashlib, secrets, time
from db import users_col, sessions_col
from datetime import datetime, timedelta

SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL", 3600*24))  # 24h

def hash_password(password: str) -> str:
    # simple sha256 (for demo). Replace with bcrypt in prod.
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash_):
    return hash_password(password) == hash_

def create_user(username, email, password):
    if users_col().find_one({"username": username}):
        raise ValueError("username exists")
    return users_col().insert_one({
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "role": "user",
        "created_at": datetime.utcnow()
    }).inserted_id

def create_session(user_id):
    token = secrets.token_hex(32)
    now = datetime.utcnow()
    sessions_col().insert_one({
        "user_id": user_id,
        "token": token,
        "created_at": now,
        "expires_at": now + timedelta(seconds=SESSION_TTL_SECONDS)
    })
    return token

def get_user_by_token(token):
    s = sessions_col().find_one({"token": token, "expires_at": {"$gt": datetime.utcnow()}})
    if not s:
        return None
    return users_col().find_one({"_id": s["user_id"]})
