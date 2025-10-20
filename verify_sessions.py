"""
verify_sessions.py

Verify session-event consistency and report issues.
"""

from db import sessions_col, events_col
from bson import ObjectId

def verify_all_sessions():
    """Comprehensive verification of all sessions."""
    
    print("=" * 60)
    print("Session Verification Report")
    print("=" * 60)
    
    # Get counts
    total_sessions = sessions_col().count_documents({})
    total_events = events_col().count_documents({})
    
    print(f"\n📊 Overall Stats:")
    print(f"  Total sessions: {total_sessions}")
    print(f"  Total events: {total_events}")
    
    # Check 1: Sessions with empty pages
    empty_pages = sessions_col().count_documents({
        "$or": [
            {"pages": {"$exists": False}},
            {"pages": {"$size": 0}}
        ]
    })
    
    print(f"\n1️⃣ Empty Pages:")
    print(f"  Sessions with empty pages: {empty_pages}")
    if empty_pages > 0:
        print(f"  ⚠️  {empty_pages} sessions need page data")
    else:
        print(f"  ✅ All sessions have pages")
    
    # Check 2: Sessions with 0 events
    zero_events = sessions_col().count_documents({
        "$or": [
            {"event_count": 0},
            {"event_count": {"$exists": False}}
        ]
    })
    
    print(f"\n2️⃣ Event Counts:")
    print(f"  Sessions with 0 events: {zero_events}")
    if zero_events > 0:
        print(f"  ⚠️  {zero_events} sessions report 0 events")
    else:
        print(f"  ✅ All sessions have events")
    
    # Check 3: Orphan sessions (session exists but no events in DB)
    print(f"\n3️⃣ Orphan Sessions:")
    print(f"  Checking for sessions without matching events...")
    
    orphan_count = 0
    sample_orphans = []
    
    for session in sessions_col().find().limit(1000):  # Check sample
        session_id = session.get("session_id")
        event_count = events_col().count_documents({"session_id": session_id})
        
        if event_count == 0:
            orphan_count += 1
            if len(sample_orphans) < 5:
                sample_orphans.append(session_id)
    
    print(f"  Orphan sessions (in sample of 1000): {orphan_count}")
    if orphan_count > 0:
        print(f"  ⚠️  Sample orphan IDs: {sample_orphans[:3]}")
    else:
        print(f"  ✅ No orphan sessions in sample")
    
    # Check 4: Events without sessions
    print(f"\n4️⃣ Orphan Events:")
    print(f"  Checking for events without matching sessions...")
    
    distinct_session_ids = events_col().distinct("session_id")
    print(f"  Distinct session_ids in events: {len(distinct_session_ids)}")
    
    orphan_events = 0
    sample_orphan_events = []
    
    for sid in distinct_session_ids[:100]:  # Check sample
        session = sessions_col().find_one({"session_id": sid})
        if not session:
            orphan_events += 1
            if len(sample_orphan_events) < 5:
                sample_orphan_events.append(sid)
    
    print(f"  Events without sessions (in sample of 100): {orphan_events}")
    if orphan_events > 0:
        print(f"  ⚠️  Sample session IDs: {sample_orphan_events[:3]}")
    else:
        print(f"  ✅ All events have matching sessions")
    
    # Check 5: Mismatched counts
    print(f"\n5️⃣ Mismatched Counts:")
    print(f"  Verifying event_count accuracy...")
    
    mismatched = 0
    sample_mismatched = []
    
    for session in sessions_col().find().limit(100):  # Check sample
        session_id = session.get("session_id")
        reported_count = session.get("event_count", 0)
        actual_count = events_col().count_documents({"session_id": session_id})
        
        if reported_count != actual_count:
            mismatched += 1
            if len(sample_mismatched) < 3:
                sample_mismatched.append({
                    "session_id": session_id,
                    "reported": reported_count,
                    "actual": actual_count
                })
    
    print(f"  Mismatched counts (in sample of 100): {mismatched}")
    if mismatched > 0:
        print(f"  ⚠️  Sample mismatches:")
        for mm in sample_mismatched:
            print(f"     {mm['session_id']}: reported={mm['reported']}, actual={mm['actual']}")
    else:
        print(f"  ✅ All event counts are accurate")
    
    # Check 6: User ID consistency
    print(f"\n6️⃣ User ID Consistency:")
    print(f"  Checking if events match session user_id...")
    
    inconsistent_users = 0
    sample_inconsistent = []
    
    for session in sessions_col().find().limit(100):  # Check sample
        session_id = session.get("session_id")
        session_user_id = str(session.get("user_id"))
        
        event_users = events_col().distinct("user_id", {"session_id": session_id})
        event_users_str = [str(u) for u in event_users]
        
        if len(event_users_str) > 1 or (len(event_users_str) == 1 and event_users_str[0] != session_user_id):
            inconsistent_users += 1
            if len(sample_inconsistent) < 3:
                sample_inconsistent.append({
                    "session_id": session_id,
                    "session_user": session_user_id,
                    "event_users": event_users_str
                })
    
    print(f"  Inconsistent user_ids (in sample of 100): {inconsistent_users}")
    if inconsistent_users > 0:
        print(f"  ⚠️  Sample inconsistencies:")
        for ic in sample_inconsistent:
            print(f"     Session {ic['session_id'][:16]}...: user={ic['session_user'][-6:]}, events={[u[-6:] for u in ic['event_users']]}")
    else:
        print(f"  ✅ All user_ids are consistent")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    issues = []
    if empty_pages > 0:
        issues.append(f"{empty_pages} sessions with empty pages")
    if zero_events > 0:
        issues.append(f"{zero_events} sessions with 0 events")
    if orphan_count > 0:
        issues.append(f"~{orphan_count * (total_sessions / 1000):.0f} orphan sessions (estimated)")
    if orphan_events > 0:
        issues.append(f"~{orphan_events * (len(distinct_session_ids) / 100):.0f} orphan events (estimated)")
    if mismatched > 0:
        issues.append(f"~{mismatched * (total_sessions / 100):.0f} mismatched counts (estimated)")
    if inconsistent_users > 0:
        issues.append(f"~{inconsistent_users * (total_sessions / 100):.0f} inconsistent user_ids (estimated)")
    
    if len(issues) == 0:
        print("\n✅ ✅ ✅ All checks passed! Database is healthy! ✅ ✅ ✅")
    else:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nRun fix_empty_sessions.py to fix empty sessions")
        print("Run fix_duplicate_sessions.py to fix duplicates")

if __name__ == "__main__":
    verify_all_sessions()
