"""
fix_empty_sessions.py

Fix sessions với pages empty và event_count = 0 bằng cách:
1. Tìm events matching session_id
2. Tính toán lại pages, event_count, timestamps
3. Update session document
"""

from db import sessions_col, events_col
from datetime import datetime
import pytz

def find_empty_sessions():
    """Find sessions with empty pages and 0 events."""
    empty_sessions = list(sessions_col().find({
        "$or": [
            {"pages": {"$exists": False}},
            {"pages": {"$size": 0}},
            {"event_count": 0},
            {"event_count": {"$exists": False}}
        ]
    }))
    
    print(f"Found {len(empty_sessions)} potentially empty sessions")
    return empty_sessions

def fix_session(session):
    """Fix a single session by recalculating from its events."""
    session_id = session.get("session_id")
    
    # Find all events for this session
    events = list(events_col().find({"session_id": session_id}))
    
    if len(events) == 0:
        # Truly empty - might be orphan session created by ensure_browsing_session
        return None
    
    # Calculate correct values from events
    pages = list(set([e.get("page") for e in events if e.get("page")]))
    event_count = len(events)
    
    timestamps = [e.get("timestamp") for e in events if e.get("timestamp")]
    first_event_at = min(timestamps) if timestamps else None
    last_event_at = max(timestamps) if timestamps else None
    
    # Get client_id and user_id from first event
    first_event = events[0]
    client_id = first_event.get("client_id")
    user_id = first_event.get("user_id")
    
    # Update session
    update_doc = {
        "pages": pages,
        "event_count": event_count,
        "client_id": client_id,
        "user_id": user_id
    }
    
    if first_event_at:
        update_doc["first_event_at"] = first_event_at
    if last_event_at:
        update_doc["last_event_at"] = last_event_at
    
    sessions_col().update_one(
        {"session_id": session_id},
        {"$set": update_doc}
    )
    
    return {
        "session_id": session_id,
        "pages_count": len(pages),
        "event_count": event_count
    }

def main():
    print("=" * 60)
    print("Fix Empty Sessions Script")
    print("=" * 60)
    
    # Step 1: Find empty sessions
    empty_sessions = find_empty_sessions()
    
    if len(empty_sessions) == 0:
        print("\n✅ No empty sessions found!")
        return
    
    # Step 2: Fix each session
    fixed_count = 0
    orphan_count = 0
    
    print(f"\nProcessing {len(empty_sessions)} sessions...")
    
    for i, session in enumerate(empty_sessions):
        result = fix_session(session)
        
        if result is None:
            orphan_count += 1
        else:
            fixed_count += 1
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(empty_sessions)}...")
    
    print("\n" + "=" * 60)
    print(f"✅ Fixed {fixed_count} sessions")
    print(f"ℹ️  Found {orphan_count} orphan sessions (no events)")
    print("=" * 60)
    
    # Step 3: Verify
    print("\n=== Verification ===")
    remaining_empty = sessions_col().count_documents({
        "$or": [
            {"pages": {"$size": 0}},
            {"event_count": 0}
        ]
    })
    
    total_sessions = sessions_col().count_documents({})
    sessions_with_events = sessions_col().count_documents({"event_count": {"$gt": 0}})
    
    print(f"Total sessions: {total_sessions}")
    print(f"Sessions with events: {sessions_with_events}")
    print(f"Empty sessions remaining: {remaining_empty}")
    
    if remaining_empty == orphan_count:
        print("\n✅ All fixable sessions have been fixed!")
        print(f"   {orphan_count} orphan sessions remain (created but no events)")
    else:
        print(f"\n⚠️  {remaining_empty - orphan_count} sessions still need attention")

if __name__ == "__main__":
    main()
