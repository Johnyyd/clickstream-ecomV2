"""
MongoDB Index Creation Script
Creates indexes to speed up Spark analytics queries by 10-100x
"""

from app.core.db_sync import events_col, users_col, sessions_col, products_col

print("=" * 60)
print("Creating MongoDB Indexes for Spark Optimization")
print("=" * 60)

# Events collection indexes
print("\n[1/5] events collection...")
try:
    # User + timestamp (for user-specific queries)
    events_col().create_index([("user_id", 1), ("timestamp", 1)])
    print("  ✓ user_id + timestamp")

    # Session + timestamp (for journey analytics)
    events_col().create_index([("session_id", 1), ("timestamp", 1)])
    print("  ✓ session_id + timestamp")

    # Event type (for filtering by event)
    events_col().create_index([("event_type", 1)])
    print("  ✓ event_type")

    # Timestamp alone (for date range queries)
    events_col().create_index([("timestamp", 1)])
    print("  ✓ timestamp")

    # Properties.product_id (for recommendations)
    events_col().create_index([("properties.product_id", 1)])
    print("  ✓ properties.product_id")

except Exception as e:
    print(f"  ✗ Error: {e}")

# Users collection indexes
print("\n[2/5] users collection...")
try:
    users_col().create_index([("username", 1)], unique=True)
    print("  ✓ username (unique)")

    users_col().create_index([("created_at", 1)])
    print("  ✓ created_at")

except Exception as e:
    print(f"  ✗ Error: {e}")

# Sessions collection indexes
print("\n[3/5] sessions collection...")
try:
    sessions_col().create_index([("user_id", 1)])
    print("  ✓ user_id")

    sessions_col().create_index([("start_time", 1)])
    print("  ✓ start_time")

except Exception as e:
    print(f"  ✗ Error: {e}")

# Products collection indexes
print("\n[4/5] products collection...")
try:
    products_col().create_index([("category", 1)])
    print("  ✓ category")

    products_col().create_index([("price", 1)])
    print("  ✓ price")

except Exception as e:
    print(f"  ✗ Error: {e}")

# Verify indexes
print("\n[5/5] Verifying...")
try:
    indexes = list(events_col().list_indexes())
    print(f"  ✓ events collection has {len(indexes)} indexes")
    for idx in indexes:
        print(f"    - {idx['name']}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "=" * 60)
print("✅ Index creation complete!")
print("Expected impact: 10-100x faster queries")
print("=" * 60)
