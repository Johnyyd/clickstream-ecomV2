# test_complete_flow.py - Test complete flow with consistent IDs
from simulate_clickstream import simulate_realistic_ecommerce
from analysis import run_analysis
from db import events_col, analyses_col
from bson import ObjectId
import json

def test_complete_flow():
    print("=== Complete Clickstream Analysis Flow Test ===")
    
    # 1. Generate realistic e-commerce data
    print("\n1. Generating realistic e-commerce data...")
    total_events = simulate_realistic_ecommerce(30)  # 30 sessions
    print(f"✅ Generated {total_events} events")
    
    # 2. Check data quality
    print("\n2. Checking data quality...")
    events = list(events_col().find().limit(5))
    
    print("Sample events:")
    for i, event in enumerate(events):
        print(f"  Event {i+1}: User {event.get('user_id')} | Session {event.get('session_id')} | Page {event.get('page')} | Type {event.get('event_type')}")
    
    # 3. Run analysis
    print("\n3. Running analysis...")
    
    # Get a user ID from events
    sample_user_id = events[0]['user_id'] if events else None
    if not sample_user_id:
        print("❌ No events found, cannot run analysis")
        return False
    
    print(f"Running analysis for user: {sample_user_id}")
    
    try:
        analysis_result = run_analysis(str(sample_user_id), {"limit": 1000})
        print("✅ Analysis completed successfully")
        
        # 4. Check analysis results
        print("\n4. Checking analysis results...")
        
        # Get the saved analysis from database
        saved_analysis = analyses_col().find_one({"_id": analysis_result["_id"]})
        
        if saved_analysis:
            print("✅ Analysis saved to database")
            
            # Check basic metrics
            basic_metrics = saved_analysis.get("detailed_metrics", {}).get("basic_metrics", {})
            print(f"  - Total events: {basic_metrics.get('total_events', 0)}")
            print(f"  - Total sessions: {basic_metrics.get('total_sessions', 0)}")
            print(f"  - Unique users: {basic_metrics.get('unique_users', 0)}")
            print(f"  - Bounce rate: {basic_metrics.get('bounce_rate', 0):.2%}")
            
            # Check funnel analysis
            funnel_analysis = saved_analysis.get("detailed_metrics", {}).get("funnel_analysis", {})
            if funnel_analysis:
                print("  - Funnel analysis:")
                for funnel_name, funnel_data in funnel_analysis.items():
                    if funnel_data.get("conversion", 0) > 0:
                        print(f"    {funnel_name}: {funnel_data['conversion']:.1%} conversion")
            
            # Check insights
            insights = saved_analysis.get("insights", {})
            if insights:
                print("  - Key findings:")
                for finding in insights.get("key_findings", [])[:3]:  # Show first 3
                    print(f"    • {finding}")
            
            return True
        else:
            print("❌ Analysis not found in database")
            return False
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

def test_id_consistency_advanced():
    """Advanced ID consistency test"""
    print("\n=== Advanced ID Consistency Test ===")
    
    # Get all events
    events = list(events_col().find())
    print(f"Total events in database: {len(events)}")
    
    # Check user ID consistency
    user_ids = set()
    session_ids = set()
    
    for event in events:
        if event.get('user_id'):
            user_ids.add(event['user_id'])
        if event.get('session_id'):
            session_ids.add(event['session_id'])
    
    print(f"Unique user IDs: {len(user_ids)}")
    print(f"Unique session IDs: {len(session_ids)}")
    
    # Check for events with same session but different users (should not happen)
    session_user_map = {}
    conflicts = []
    
    for event in events:
        session_id = event.get('session_id')
        user_id = event.get('user_id')
        
        if session_id and user_id:
            if session_id in session_user_map:
                if session_user_map[session_id] != user_id:
                    conflicts.append((session_id, session_user_map[session_id], user_id))
            else:
                session_user_map[session_id] = user_id
    
    if conflicts:
        print(f"❌ Found {len(conflicts)} session-user conflicts:")
        for session_id, user1, user2 in conflicts[:5]:  # Show first 5
            print(f"  Session {session_id}: User {user1} vs User {user2}")
    else:
        print("✅ No session-user conflicts found")
    
    # Check for events with same user but different sessions (this is OK)
    user_session_map = {}
    for event in events:
        session_id = event.get('session_id')
        user_id = event.get('user_id')
        
        if session_id and user_id:
            if user_id not in user_session_map:
                user_session_map[user_id] = set()
            user_session_map[user_id].add(session_id)
    
    print(f"Users with multiple sessions:")
    for user_id, sessions in user_session_map.items():
        if len(sessions) > 1:
            print(f"  User {user_id}: {len(sessions)} sessions")
    
    return len(conflicts) == 0

if __name__ == "__main__":
    print("Starting complete flow test...")
    
    # Test complete flow
    flow_success = test_complete_flow()
    
    # Test ID consistency
    id_consistency = test_id_consistency_advanced()
    
    print(f"\n=== Final Results ===")
    print(f"Complete Flow: {'✅ PASS' if flow_success else '❌ FAIL'}")
    print(f"ID Consistency: {'✅ PASS' if id_consistency else '❌ FAIL'}")
    
    if flow_success and id_consistency:
        print("\n🎉 All tests passed! The system is working correctly with consistent IDs.")
    else:
        print("\n⚠️ Some tests failed. Please check the issues above.")
