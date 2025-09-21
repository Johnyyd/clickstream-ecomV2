# db.py
from pymongo import MongoClient
import os

MONGO_URI = os.environ.get("MONGO_URI","mongodb://localhost:27017")
DB_NAME = os.environ.get("MONGO_DB","clickstream_db")

_client = None
_db = None

def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client

def get_db():
    global _db
    if _db is None:
        _db = get_client()[DB_NAME]
    return _db

# helpers
def users_col(): return get_db().users
def events_col(): return get_db().events
def analyses_col(): return get_db().analyses
def sessions_col(): return get_db().sessions
def api_keys_col(): return get_db().api_keys
def products_col(): return get_db().products
