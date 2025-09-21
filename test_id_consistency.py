# test_id_consistency.py - Test ID consistency across the system
from simulate_clickstream import simulate, get_or_create_test_users
from db import events_col, users_col
from bson import ObjectId
import json

def test_id_consistency():
    print("=== Testing ID Consistency ===")
    
    # 1. Check existing users
    print("\n1. Checking existing users...")
    users = get_or_create_test_users()
    print(f"Found {len(users)} users:")
    for user in users:
        print(f"  - {user['username']}: {user['_id']} (type: {type(user['_id'])})")
    
    # 2. Run simulation
    print("\n2. Running simulation...")
    total_events = simulate(5, seed_products_first=True)
    print(f"Generated {total_events} events")
    
    # 3. Check events in database
    print("\n3. Checking events in database...")
    events = list(events_col().find().limit(10))
    
    print(f"Sample events:")
    for i, event in enumerate(events):
        print(f"\nEvent {i+1}:")
        print(f"  - Event ID: {event['_id']}")
        print(f"  - User ID: {event.get('user_id', 'None')} (type: {type(event.get('user_id'))})")
        print(f"  - Session ID: {event.get('session_id', 'None')} (type: {type(event.get('session_id'))})")
        print(f"  - Client ID: {event.get('client_id', 'None')} (type: {type(event.get('client_id'))})")
        print(f"  - Page: {event.get('page', 'None')}")
        print(f"  - Event Type: {event.get('event_type', 'None')}")
        print(f"  - Properties: {event.get('properties', {})}")
    
    # 4. Check user ID consistency
    print("\n4. Checking user ID consistency...")
    user_ids_in_events = set()
    for event in events:
        if event.get('user_id'):
            user_ids_in_events.add(event['user_id'])
    
    print(f"User IDs found in events: {user_ids_in_events}")
    
    # Check if user IDs in events match actual user IDs
    actual_user_ids = {user['_id'] for user in users}  # Keep as ObjectId
    print(f"Actual user IDs in database: {actual_user_ids}")
    
    # Find mismatches
    mismatches = user_ids_in_events - actual_user_ids
    if mismatches:
        print(f"❌ ID Mismatches found: {mismatches}")
    else:
        print("✅ All user IDs in events match database users")
    
    # 5. Check session ID patterns
    print("\n5. Checking session ID patterns...")
    session_ids = [event.get('session_id') for event in events if event.get('session_id')]
    print(f"Session IDs: {session_ids}")
    
    # Check if session IDs follow expected pattern
    expected_pattern = any(sid.startswith('session_') for sid in session_ids)
    if expected_pattern:
        print("✅ Session IDs follow expected pattern")
    else:
        print("❌ Session IDs don't follow expected pattern")
    
    # 6. Check for null/empty IDs
    print("\n6. Checking for null/empty IDs...")
    null_user_ids = sum(1 for event in events if not event.get('user_id'))
    null_session_ids = sum(1 for event in events if not event.get('session_id'))
    
    print(f"Events with null user_id: {null_user_ids}")
    print(f"Events with null session_id: {null_session_ids}")
    
    if null_user_ids == 0 and null_session_ids == 0:
        print("✅ No null IDs found")
    else:
        print("❌ Found null IDs - this needs to be fixed")
    
    return {
        "total_events": len(events),
        "user_id_matches": len(mismatches) == 0,
        "session_id_pattern": expected_pattern,
        "no_null_ids": null_user_ids == 0 and null_session_ids == 0
    }

if __name__ == "__main__":
    result = test_id_consistency()
    print(f"\n=== Test Results ===")
    print(f"User ID Consistency: {'✅ PASS' if result['user_id_matches'] else '❌ FAIL'}")
    print(f"Session ID Pattern: {'✅ PASS' if result['session_id_pattern'] else '❌ FAIL'}")
    print(f"No Null IDs: {'✅ PASS' if result['no_null_ids'] else '❌ FAIL'}")
