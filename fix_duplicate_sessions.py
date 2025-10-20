"""
fix_duplicate_sessions.py

Fix duplicate session documents caused by inconsistent query methods.
- Old: Query by _id field
- New: Query by session_id field

This script:
1. Finds duplicate sessions (same session_id)
2. Merges them into one
3. Updates event references
4. Cleans up duplicates
"""

from db import sessions_col, events_col
from bson import ObjectId

def find_duplicate_sessions():
    """Find session_ids that have multiple documents."""
    pipeline = [
        {
            "$group": {
                "_id": "$session_id",
                "count": {"$sum": 1},
                "docs": {"$push": "$$ROOT"}
            }
        },
        {
            "$match": {"count": {"$gt": 1}}
        }
    ]
    
    duplicates = list(sessions_col().aggregate(pipeline))
    print(f"Found {len(duplicates)} duplicate session_ids")
    return duplicates

def merge_and_cleanup_sessions(duplicates):
    """Merge duplicate sessions and keep the one with most data."""
    total_merged = 0
    total_deleted = 0
    
    for dup in duplicates:
        session_id = dup["_id"]
        docs = dup["docs"]
        
        # Sort by event_count desc, then by first_event_at asc
        docs.sort(key=lambda d: (
            -(d.get("event_count") or 0),
            d.get("first_event_at") or datetime.min
        ))
        
        # Keep the first one (most events)
        keeper = docs[0]
        to_delete = docs[1:]
        
        print(f"\nSession: {session_id}")
        print(f"  Keeper: {keeper['_id']} (events: {keeper.get('event_count', 0)})")
        print(f"  Deleting: {[str(d['_id']) for d in to_delete]}")
        
        # Merge data from duplicates into keeper
        all_pages = set(keeper.get("pages", []))
        max_last_event = keeper.get("last_event_at")
        min_first_event = keeper.get("first_event_at")
        total_events = keeper.get("event_count", 0)
        
        for doc in to_delete:
            all_pages.update(doc.get("pages", []))
            if doc.get("last_event_at") and (not max_last_event or doc["last_event_at"] > max_last_event):
                max_last_event = doc["last_event_at"]
            if doc.get("first_event_at") and (not min_first_event or doc["first_event_at"] < min_first_event):
                min_first_event = doc["first_event_at"]
            total_events += doc.get("event_count", 0)
        
        # Update keeper with merged data
        sessions_col().update_one(
            {"_id": keeper["_id"]},
            {
                "$set": {
                    "pages": list(all_pages),
                    "last_event_at": max_last_event,
                    "first_event_at": min_first_event,
                    "event_count": total_events
                }
            }
        )
        
        # Delete duplicates
        for doc in to_delete:
            sessions_col().delete_one({"_id": doc["_id"]})
            total_deleted += 1
        
        total_merged += 1
    
    print(f"\n✅ Merged {total_merged} sessions")
    print(f"✅ Deleted {total_deleted} duplicate documents")
    return total_merged, total_deleted

def verify_sessions():
    """Verify all sessions have correct user_id and events."""
    print("\n=== Verifying Sessions ===")
    
    # Check sessions without events
    sessions = list(sessions_col().find())
    print(f"Total sessions: {len(sessions)}")
    
    sessions_without_events = 0
    sessions_with_wrong_user = 0
    
    for session in sessions:
        session_id = session.get("session_id")
        user_id = session.get("user_id")
        
        # Check if events exist
        events = list(events_col().find({"session_id": session_id}))
        
        if len(events) == 0:
            sessions_without_events += 1
        else:
            # Check if all events have same user_id
            event_users = set([str(e.get("user_id")) for e in events if e.get("user_id")])
            if len(event_users) > 1 or (len(event_users) == 1 and str(user_id) not in event_users):
                sessions_with_wrong_user += 1
                print(f"  ⚠️  Session {session_id}: user_id={user_id}, but events have users={event_users}")
    
    print(f"\n📊 Results:")
    print(f"  Sessions without events: {sessions_without_events}")
    print(f"  Sessions with wrong user_id: {sessions_with_wrong_user}")
    
    if sessions_without_events == 0 and sessions_with_wrong_user == 0:
        print("\n✅ All sessions are valid!")
    else:
        print("\n⚠️  Some sessions need attention")
    
    return sessions_without_events, sessions_with_wrong_user

def main():
    print("=" * 60)
    print("Fix Duplicate Sessions Script")
    print("=" * 60)
    
    # Step 1: Find duplicates
    duplicates = find_duplicate_sessions()
    
    if len(duplicates) == 0:
        print("\n✅ No duplicate sessions found!")
    else:
        # Step 2: Merge and cleanup
        merged, deleted = merge_and_cleanup_sessions(duplicates)
    
    # Step 3: Verify
    verify_sessions()
    
    print("\n" + "=" * 60)
    print("✅ Done!")
    print("=" * 60)

if __name__ == "__main__":
    from datetime import datetime
    main()
