# simple_analysis.py - Simplified analysis without Spark
from db import events_col
from datetime import datetime
from collections import Counter, defaultdict
import json

def simple_sessionize_and_counts(limit=None, user_id=None):
    """Simple analysis without Spark for small datasets"""
    try:
        print("\n=== Starting Simple Analysis ===")
        print(f"Limit parameter: {limit}")
        if user_id:
            print(f"Filtering by user_id: {user_id}")
        
        # Load events from MongoDB
        q = {}
        if user_id is not None:
            # Events may store user_id as ObjectId or string; filter for both
            try:
                from bson import ObjectId
                oid = ObjectId(str(user_id))
                q["$or"] = [{"user_id": oid}, {"user_id": str(user_id)}]
            except Exception:
                q["user_id"] = str(user_id)
        cursor = events_col().find(q).sort("timestamp", 1)
        if limit:
            cursor = cursor.limit(limit)
        
        events = list(cursor)
        print(f"Loaded {len(events)} events from MongoDB")
        
        # Debug: show first few events
        if events:
            print("First event sample:")
            sample_event = events[0]
            print(f"  - _id: {sample_event.get('_id')}")
            print(f"  - page: {sample_event.get('page')}")
            print(f"  - session_id: {sample_event.get('session_id')}")
            print(f"  - timestamp: {sample_event.get('timestamp')}")
        
        if not events:
            print("No events found in MongoDB")
            return {"total_events": 0, "sessions": 0, "top_pages": [], "funnel_home_to_product": 0}
        
        # Process events
        total_events = len(events)
        sessions = set()
        page_counts = Counter()
        home_sessions = set()
        product_sessions = set()
        
        for event in events:
            # Get session_id
            session_id = str(event.get("session_id", ""))
            if session_id:
                sessions.add(session_id)
            
            # Get page
            page = str(event.get("page", ""))
            if page:
                page_counts[page] += 1
                
                # Track home and product page sessions
                if page == "/home":
                    home_sessions.add(session_id)
                elif page == "/product":
                    product_sessions.add(session_id)
        
        # Calculate metrics
        unique_sessions = len(sessions)
        top_pages = [{"page": page, "count": count} for page, count in page_counts.most_common(10)]
        funnel_home_to_product = len(home_sessions.intersection(product_sessions))
        
        result = {
            "total_events": total_events,
            "sessions": unique_sessions,
            "top_pages": top_pages,
            "funnel_home_to_product": funnel_home_to_product
        }
        
        print(f"Analysis completed:")
        print(f"- Total events: {total_events}")
        print(f"- Unique sessions: {unique_sessions}")
        print(f"- Top pages: {top_pages[:5]}")
        print(f"- Home to product conversion: {funnel_home_to_product}")
        
        return result
        
    except Exception as e:
        print(f"Error in simple analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "total_events": 0,
            "sessions": 0,
            "top_pages": [],
            "funnel_home_to_product": 0
        }

if __name__ == "__main__":
    result = simple_sessionize_and_counts(limit=100)
    print("\nFinal result:", json.dumps(result, indent=2))
