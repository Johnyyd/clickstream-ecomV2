"""
List Active Users for ALS Testing
Shows users who have product interactions
"""

from db import events_col, users_col
from collections import Counter

def list_active_users(min_interactions=5, limit=20):
    """List users with product interactions"""
    
    print("\n" + "="*70)
    print("👥 ACTIVE USERS FOR ALS RECOMMENDATIONS")
    print("="*70)
    
    # Get product interaction events
    pipeline = [
        {
            "$match": {
                "properties.product_id": {"$exists": True, "$ne": ""},
                "user_id": {"$exists": True}
            }
        },
        {
            "$group": {
                "_id": "$user_id",
                "total_interactions": {"$sum": 1},
                "pageviews": {
                    "$sum": {"$cond": [{"$eq": ["$event_type", "pageview"]}, 1, 0]}
                },
                "add_to_carts": {
                    "$sum": {"$cond": [{"$eq": ["$event_type", "add_to_cart"]}, 1, 0]}
                },
                "purchases": {
                    "$sum": {"$cond": [{"$eq": ["$event_type", "purchase"]}, 1, 0]}
                },
                "unique_products": {"$addToSet": "$properties.product_id"}
            }
        },
        {
            "$match": {
                "total_interactions": {"$gte": min_interactions}
            }
        },
        {
            "$sort": {"total_interactions": -1}
        },
        {
            "$limit": limit
        }
    ]
    
    user_stats = list(events_col().aggregate(pipeline))
    
    if not user_stats:
        print(f"\n❌ No users found with at least {min_interactions} product interactions")
        print("   Run: python seed_realistic_data.py")
        return
    
    print(f"\nFound {len(user_stats)} users with {min_interactions}+ product interactions\n")
    
    # Get usernames
    user_details = []
    for stat in user_stats:
        user_id = stat["_id"]
        user = users_col().find_one({"_id": user_id})
        
        if user:
            user_details.append({
                "username": user.get("username", "N/A"),
                "email": user.get("email", "N/A"),
                "total_interactions": stat["total_interactions"],
                "pageviews": stat["pageviews"],
                "add_to_carts": stat["add_to_carts"],
                "purchases": stat["purchases"],
                "unique_products": len(stat["unique_products"])
            })
    
    # Display table
    print(f"{'#':<4} {'Username':<20} {'Interactions':<15} {'Products':<10} {'Purchases':<10}")
    print("-" * 70)
    
    for i, user in enumerate(user_details, 1):
        print(f"{i:<4} {user['username']:<20} "
              f"{user['total_interactions']:<15} "
              f"{user['unique_products']:<10} "
              f"{user['purchases']:<10}")
    
    # Show example API calls
    print("\n" + "="*70)
    print("🚀 TEST ALS RECOMMENDATIONS")
    print("="*70)
    
    if user_details:
        example_user = user_details[0]['username']
        print(f"\n1. Via API:")
        print(f"   GET /api/analytics/recommendations/{example_user}")
        
        print(f"\n2. Via Python:")
        print(f"   from spark_recommendation_als import ml_product_recommendations_als")
        print(f"   result = ml_product_recommendations_als(username='{example_user}')")
        
        print(f"\n3. Via curl:")
        print(f"   curl http://localhost:5001/api/analytics/recommendations/{example_user}")
    
    # Summary statistics
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    
    total_interactions = sum(u['total_interactions'] for u in user_details)
    total_purchases = sum(u['purchases'] for u in user_details)
    avg_interactions = total_interactions / len(user_details) if user_details else 0
    
    print(f"\nTotal users shown: {len(user_details)}")
    print(f"Total interactions: {total_interactions}")
    print(f"Total purchases: {total_purchases}")
    print(f"Avg interactions per user: {avg_interactions:.1f}")
    
    # Distribution
    print("\n📈 Interaction Distribution:")
    buckets = [
        ("5-10", 5, 10),
        ("11-50", 11, 50),
        ("51-100", 51, 100),
        ("101-500", 101, 500),
        ("500+", 501, float('inf'))
    ]
    
    for label, min_val, max_val in buckets:
        count = sum(1 for u in user_details if min_val <= u['total_interactions'] < max_val)
        if count > 0:
            print(f"  {label:>10} interactions: {count} users")

def show_user_details(username):
    """Show detailed product interactions for specific user"""
    
    print("\n" + "="*70)
    print(f"🔍 USER DETAILS: {username}")
    print("="*70)
    
    user = users_col().find_one({"username": username})
    if not user:
        print(f"\n❌ User '{username}' not found")
        return
    
    # Get all product interactions
    events = list(events_col().find({
        "user_id": user["_id"],
        "properties.product_id": {"$exists": True, "$ne": ""}
    }).sort("timestamp", 1))
    
    if not events:
        print(f"\n❌ User '{username}' has no product interactions")
        print("   This user cannot receive ALS recommendations yet")
        return
    
    print(f"\nTotal product interactions: {len(events)}")
    
    # Event type breakdown
    event_types = Counter(e.get("event_type") for e in events)
    print("\nEvent Types:")
    for event_type, count in event_types.most_common():
        print(f"  {event_type}: {count}")
    
    # Products interacted
    products = set(e.get("properties", {}).get("product_id") for e in events)
    print(f"\nUnique products interacted: {len(products)}")
    
    # Recent interactions
    print("\n📝 Recent 5 Interactions:")
    for i, event in enumerate(events[-5:], 1):
        product_id = event.get("properties", {}).get("product_id", "N/A")
        product_name = event.get("properties", {}).get("product_name", "N/A")
        event_type = event.get("event_type")
        timestamp = event.get("timestamp", "N/A")
        
        print(f"  {i}. [{event_type}] {product_name[:30]}")
        print(f"     Product ID: {product_id}")
        print(f"     Time: {timestamp}")
        print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Show details for specific user
        username = sys.argv[1]
        show_user_details(username)
    else:
        # List all active users
        try:
            list_active_users(min_interactions=5, limit=20)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
