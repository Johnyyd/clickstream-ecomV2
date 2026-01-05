"""
Check ALS Data Readiness
Diagnostic script to verify product interaction data for ALS recommendations
"""

from app.core.db_sync import events_col, products_col, users_col
from collections import Counter

def check_als_readiness():
    """Check if database has sufficient data for ALS recommendations"""
    
    print("\n" + "="*70)
    print("🔍 ALS RECOMMENDATION DATA CHECKER")
    print("="*70)
    
    # 1. Check products
    print("\n📦 Products Check:")
    product_count = products_col().count_documents({})
    print(f"  Total products: {product_count}")
    
    if product_count == 0:
        print("  ❌ No products found!")
        print("  → Run: python seed_realistic_data.py")
        return False
    elif product_count < 5:
        print(f"  ⚠️  Only {product_count} products. Recommend at least 10+")
    else:
        print(f"  ✅ Good: {product_count} products available")
    
    # 2. Check users
    print("\n👥 Users Check:")
    user_count = users_col().count_documents({})
    print(f"  Total users: {user_count}")
    
    if user_count < 2:
        print(f"  ❌ Need at least 2 users for collaborative filtering")
        return False
    else:
        print(f"  ✅ Good: {user_count} users available")
    
    # 3. Check product interactions
    print("\n🔗 Product Interactions Check:")
    
    # Events with product_id in properties
    product_events = list(events_col().aggregate([
        {
            "$match": {
                "properties.product_id": {"$exists": True, "$ne": ""}
            }
        },
        {
            "$project": {
                "user_id": 1,
                "event_type": 1,
                "properties.product_id": 1
            }
        }
    ]))
    
    print(f"  Total product interaction events: {len(product_events)}")
    
    if len(product_events) == 0:
        print("  ❌ NO product interactions found!")
        print("  → Events need 'properties.product_id' field")
        print("  → Run: python seed_realistic_data.py")
        return False
    elif len(product_events) < 10:
        print(f"  ⚠️  Only {len(product_events)} interactions. ALS works better with 50+")
    else:
        print(f"  ✅ Good: {len(product_events)} product interactions")
    
    # 4. Analyze interaction details
    print("\n📊 Interaction Details:")
    
    # Unique users with interactions
    users_with_interactions = set(str(e.get("user_id")) for e in product_events)
    print(f"  Users with product interactions: {len(users_with_interactions)}")
    
    # Unique products interacted
    products_interacted = set(
        e.get("properties", {}).get("product_id") 
        for e in product_events 
        if e.get("properties", {}).get("product_id")
    )
    print(f"  Unique products interacted: {len(products_interacted)}")
    
    # Event type distribution
    event_types = Counter(e.get("event_type") for e in product_events)
    print(f"  Event type breakdown:")
    for event_type, count in event_types.most_common():
        print(f"    - {event_type}: {count}")
    
    # 5. User-product matrix density
    print("\n📈 Matrix Statistics:")
    possible_interactions = len(users_with_interactions) * len(products_interacted)
    actual_interactions = len(product_events)
    density = (actual_interactions / possible_interactions * 100) if possible_interactions > 0 else 0
    
    print(f"  Matrix size: {len(users_with_interactions)} users × {len(products_interacted)} products")
    print(f"  Possible interactions: {possible_interactions}")
    print(f"  Actual interactions: {actual_interactions}")
    print(f"  Density: {density:.2f}%")
    
    if density < 0.1:
        print(f"  ⚠️  Very sparse matrix ({density:.2f}%). ALS may struggle.")
        print(f"  → Generate more interactions or reduce number of products")
    
    # 6. Sample interactions
    print("\n📝 Sample Interactions:")
    for i, event in enumerate(product_events[:3]):
        print(f"  {i+1}. User: {str(event.get('user_id'))[:8]}..., "
              f"Product: {event.get('properties', {}).get('product_id', 'N/A')[:8]}..., "
              f"Type: {event.get('event_type')}")
    
    # 7. Final verdict
    print("\n" + "="*70)
    if len(product_events) >= 10 and len(users_with_interactions) >= 2 and len(products_interacted) >= 2:
        print("✅ READY: Database has sufficient data for ALS recommendations!")
        print("   You can run: POST /api/analytics/recommendations/{username}")
        return True
    else:
        print("❌ NOT READY: Need more data for ALS recommendations")
        print("\n🔧 Actions Required:")
        if product_count < 5:
            print("   1. Seed products: python seed_realistic_data.py")
        if len(product_events) < 10:
            print("   2. Generate product interaction events")
        if len(users_with_interactions) < 2:
            print("   3. Create events from multiple users")
        print("\n   Run: python seed_realistic_data.py")
        return False

if __name__ == "__main__":
    try:
        check_als_readiness()
    except Exception as e:
        print(f"\n❌ Error checking data: {e}")
        import traceback
        traceback.print_exc()
