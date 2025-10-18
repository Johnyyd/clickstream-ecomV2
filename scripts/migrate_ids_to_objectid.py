from bson import ObjectId
from pymongo import UpdateOne
from db import events_col, sessions_col, analyses_col, users_col

def to_oid(v):
    try:
        if v is None:
            return None
        s = str(v)
        if len(s) == 24:
            return ObjectId(s)
    except Exception:
        return None
    return None

def migrate_events():
    col = events_col()
    ops = []
    batch = 0
    for doc in col.find({"$or": [{"user_id": {"$type": "string"}}, {"user_id": {"$type": 2}}]}, {"user_id": 1}):
        oid = to_oid(doc.get("user_id"))
        if oid is None:
            continue
        ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"user_id": oid}}))
        if len(ops) >= 1000:
            col.bulk_write(ops)
            batch += len(ops)
            ops = []
    if ops:
        col.bulk_write(ops)
        batch += len(ops)
    return batch

def migrate_sessions():
    col = sessions_col()
    ops = []
    batch = 0
    for doc in col.find({"$or": [{"user_id": {"$type": "string"}}, {"user_id": {"$type": 2}}]}, {"user_id": 1}):
        oid = to_oid(doc.get("user_id"))
        if oid is None:
            continue
        ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"user_id": oid}}))
        if len(ops) >= 1000:
            col.bulk_write(ops)
            batch += len(ops)
            ops = []
    if ops:
        col.bulk_write(ops)
        batch += len(ops)
    return batch

def migrate_analyses():
    col = analyses_col()
    ops = []
    batch = 0
    for doc in col.find({"$or": [{"user_id": {"$type": "string"}}, {"user_id": {"$type": 2}}]}, {"user_id": 1}):
        oid = to_oid(doc.get("user_id"))
        if oid is None:
            continue
        ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"user_id": oid}}))
        if len(ops) >= 1000:
            col.bulk_write(ops)
            batch += len(ops)
            ops = []
    if ops:
        col.bulk_write(ops)
        batch += len(ops)
    return batch

if __name__ == "__main__":
    e = migrate_events()
    s = migrate_sessions()
    a = migrate_analyses()
    print({"events_updated": e, "sessions_updated": s, "analyses_updated": a})
