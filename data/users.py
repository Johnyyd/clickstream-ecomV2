import sys
import os
# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from bson import ObjectId
import hashlib

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

sample_users = [
    {
        "_id": ObjectId(),
        "username": "alice",
        "email": "alice@example.com",
        "password_hash": hash_password("alice123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "bob",
        "email": "bob@example.com",
        "password_hash": hash_password("bob123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "charlie",
        "email": "charlie@example.com",
        "password_hash": hash_password("charlie123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "diana",
        "email": "diana@example.com",
        "password_hash": hash_password("diana123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "edward",
        "email": "edward@example.com",
        "password_hash": hash_password("edward123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "fiona",
        "email": "fiona@example.com",
        "password_hash": hash_password("fiona123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "george",
        "email": "george@example.com",
        "password_hash": hash_password("george123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "hannah",
        "email": "hannah@example.com",
        "password_hash": hash_password("hannah123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "ivan",
        "email": "ivan@example.com",
        "password_hash": hash_password("ivan123"),
        "role": "admin",   # ví dụ có 1 admin
        "created_at": datetime.now(timezone.utc)
    },
    {
        "_id": ObjectId(),
        "username": "julia",
        "email": "julia@example.com",
        "password_hash": hash_password("julia123"),
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    },
]

from db import users_col
if users_col().insert_many(sample_users):
    print("Inserted 10 users")