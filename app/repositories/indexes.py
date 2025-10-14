from pymongo import ASCENDING, DESCENDING
from db import get_db

def ensure_indexes():
    db = get_db()
    # Events
    db.events.create_index([("session_id", ASCENDING), ("timestamp", ASCENDING)], name="session_ts")
    db.events.create_index([("event_type", ASCENDING)], name="event_type")
    db.events.create_index([("page", ASCENDING)], name="page")
    db.events.create_index([("user_id", ASCENDING)], name="user_id")
    # Products
    db.products.create_index([("slug", ASCENDING)], unique=True, name="slug_unique")
    db.products.create_index([("category", ASCENDING)], name="category")
    db.products.create_index([("price", ASCENDING)], name="price")
    # Analyses
    db.analyses.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created")
    # Sessions
    db.sessions.create_index([("token", ASCENDING), ("expires_at", DESCENDING)], name="token_expiry")
    # API Keys
    db.api_keys.create_index([("user_id", ASCENDING), ("provider", ASCENDING)], unique=True, name="user_provider")
