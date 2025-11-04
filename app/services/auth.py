"""
Authentication services
Core authentication functionality for the application
"""
import os
import hashlib
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt
from passlib.context import CryptContext
from bson import ObjectId

from app.core.config import settings
from app.repositories.users_repo import UsersRepository
from app.core.db_sync import sessions_col

# Settings
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL", 3600*24))  # 24h
BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password using bcrypt with fallback support for sha256"""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hash_: str) -> bool:
    """Verify password with support for both bcrypt and legacy sha256"""
    try:
        return bcrypt.checkpw(password.encode(), str(hash_).encode())
    except Exception:
        # Backward compatibility: support old sha256 hashes
        try:
            return hashlib.sha256(password.encode()).hexdigest() == hash_
        except Exception:
            return False

def create_user(username: str, email: str, password: str) -> Dict[str, Any]:
    """Create a new user or return existing one"""
    repo = UsersRepository()
    existing = repo.find_by_username(username)
    if existing:
        return {"error": "Username already exists"}
    
    hashed = hash_password(password)
    user = repo.create({
        "username": username,
        "email": email,
        "password_hash": hashed,  # Use password_hash to match database schema
        "role": "user",  # Default role
        "created_at": datetime.utcnow()
    })
    return user

def login_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Log in a user and create a session"""
    repo = UsersRepository()
    user = repo.find_by_username(username)
    
    if not user:
        return None
    
    # Support multiple password field names: password_hash, hashed_password, password
    hashed_pwd = user.get("password_hash") or user.get("hashed_password") or user.get("password")
    if not hashed_pwd or not verify_password(password, hashed_pwd):
        return None
        
    # Create session
    session_token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)
    
    # Ensure user_id is stored correctly (handle both string and ObjectId)
    user_id = user["_id"] if isinstance(user["_id"], ObjectId) else ObjectId(user["_id"])
    
    sessions_col().insert_one({
        "token": session_token,
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "expires_at": expires
    })
    
    return {
        "token": session_token,
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user.get("email", ""),
            "role": user.get("role", "user")  # Trả về role, mặc định là "user"
        }
    }

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Get user information from session token"""
    try:
        raw = (token or "").strip()
        if raw.lower().startswith("bearer "):
            raw = raw[7:].strip()

        session = sessions_col().find_one({
            "token": raw,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        if not session:
            return None

        repo = UsersRepository()
        uid = session.get("user_id")
        try:
            uid_str = str(uid)
        except Exception:
            uid_str = uid
        return repo.get_by_id(uid_str)
    except Exception:
        return None

async def authenticate_user_async(username: str, password: str, db) -> Optional[Dict[str, Any]]:
    """Async user authentication for FastAPI"""
    user = await db.users.get_by_username(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.JWTError:
        return None

async def get_user(username: str, db):
    return await db.users.get_by_username(username)