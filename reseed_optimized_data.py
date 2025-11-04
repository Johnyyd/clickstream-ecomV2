"""
Reseed data with optimized settings for better analytics:
- Bounce rate: ~0.5%
- High product page views in top pages
- Realistic user behavior patterns
"""
import subprocess
import sys

def clear_old_data():
    """Clear old events and sessions"""
    print("🗑️  Clearing old data...")
    from app.core.db_sync import events_col, sessions_col, carts_col
    
    events_col().delete_many({})
    sessions_col().delete_many({})
    carts_col().delete_many({})
    
    print("✅ Old data cleared")

def seed_products():
    """Ensure products exist"""
    print("📦 Checking products...")
    from seed_products import seed_more_products
    from app.core.db_sync import products_col
    
    count = products_col().count_documents({})
    if count < 50:
        print(f"  Found {count} products, seeding more...")
        seed_more_products()
        count = products_col().count_documents({})
    
    print(f"✅ Products ready: {count} items")

def seed_historical_data():
    """Seed 7 days of historical data"""
    print("\n📊 Seeding historical data (7 days)...")
    cmd = [
        sys.executable,
        "seed_realistic_data.py",
        "--days", "7",
        "--user-count", "1000",
        "--sessions-per-user", "5",
        "--avg-events", "8"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"⚠️  Warning: {result.stderr}")
    
    print("✅ Historical data seeded")

def seed_recent_data():
    """Seed recent 60 minutes for real-time testing"""
    print("\n⏰ Seeding recent data (last 60 minutes)...")
    cmd = [
        sys.executable,
        "seed_realistic_data.py",
        "--recent-minutes", "60",
        "--recent-sessions", "100",
        "--user-count", "1000",
        "--avg-events", "8"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"⚠️  Warning: {result.stderr}")
    
    print("✅ Recent data seeded")

def verify_data():
    """Verify seeded data"""
    print("\n🔍 Verifying data...")
    from app.core.db_sync import events_col, sessions_col, products_col
    
    events = events_col().count_documents({})
    sessions = sessions_col().count_documents({})
    products = products_col().count_documents({})
    
    # Get sample product views
    product_views = events_col().count_documents({
        "page": {"$regex": "^/p/"}
    })
    
    # Get bounce sessions (1 event only)
    bounce_sessions = list(events_col().aggregate([
        {"$group": {
            "_id": "$session_id",
            "event_count": {"$sum": 1}
        }},
        {"$match": {"event_count": 1}},
        {"$count": "total"}
    ]))
    
    bounces = bounce_sessions[0]["total"] if bounce_sessions else 0
    bounce_rate = (bounces / sessions * 100) if sessions > 0 else 0
    
    print(f"\n📈 Data Summary:")
    print(f"  Events:        {events:,}")
    print(f"  Sessions:      {sessions:,}")
    print(f"  Products:      {products:,}")
    print(f"  Product Views: {product_views:,} ({product_views/events*100:.1f}% of events)")
    print(f"  Bounce Rate:   {bounce_rate:.2f}% ({bounces}/{sessions} sessions)")
    print()

def main():
    print("="*70)
    print("🚀 OPTIMIZED DATA SEEDING")
    print("="*70)
    print("\nThis will:")
    print("  ✓ Clear old events and sessions")
    print("  ✓ Seed products if needed")
    print("  ✓ Generate 7 days of historical data")
    print("  ✓ Generate recent 60 minutes for real-time")
    print("  ✓ Target bounce rate: ~0.5%")
    print("  ✓ High product page views")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Execute seeding
    clear_old_data()
    seed_products()
    seed_historical_data()
    seed_recent_data()
    verify_data()
    
    print("="*70)
    print("✅ SEEDING COMPLETE!")
    print("="*70)
    print("\n💡 Next steps:")
    print("  1. Refresh your browser (Ctrl+Shift+R)")
    print("  2. Click 'Run All Analytics'")
    print("  3. Check Top Pages for product views")
    print("  4. Verify bounce rate is ~0.5%")
    print()

if __name__ == "__main__":
    main()
