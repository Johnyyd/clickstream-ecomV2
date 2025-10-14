# auth.py
import os, hashlib, secrets, time
import pytz
from db import users_col, sessions_col
from datetime import datetime, timedelta
import bcrypt

SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL", 3600*24))  # 24h

def hash_password(password: str) -> str:
    # bcrypt hashing
    salt = bcrypt.gensalt(rounds=int(os.environ.get("BCRYPT_ROUNDS", "12")))
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password, hash_):
    try:
        return bcrypt.checkpw(password.encode(), str(hash_).encode())
    except Exception:
        # Backward compatibility: support old sha256 hashes
        try:
            return hashlib.sha256(password.encode()).hexdigest() == hash_
        except Exception:
            return False

def create_user(username, email, password):
    if users_col().find_one({"username": username}):
        raise ValueError("username exists")
    return users_col().insert_one({
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "role": "user",
        "created_at": datetime.now(pytz.UTC)
    }).inserted_id

def create_session(user_id):
    token = secrets.token_hex(32)
    now = datetime.now(pytz.UTC)
    sessions_col().insert_one({
        "user_id": user_id,
        "token": token,
        "created_at": now,
        "expires_at": now + timedelta(seconds=SESSION_TTL_SECONDS)
    })
    return token

def login_user(username, password):
    """Login user with username and password"""
    user = users_col().find_one({"username": username})
    if not user:
        return None, "User not found"
    
    if not verify_password(password, user["password_hash"]):
        return None, "Invalid password"
    
    # Create session
    token = create_session(user["_id"])
    return {"user": user, "token": token}, "Login successful"

def get_user_by_token(token):
    s = sessions_col().find_one({"token": token, "expires_at": {"$gt": datetime.now(pytz.UTC)}})
    if not s:
        return None
    return users_col().find_one({"_id": s["user_id"]})
