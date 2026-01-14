"""
Quick test script for SEO analytics debugging
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

print("=" * 60)
print("SEO Analytics Debug Test")
print("=" * 60)

# Test 1: Check events exist
print("\n[TEST 1] Checking events collection...")
try:
    from app.core.db_sync import events_col

    total = events_col().count_documents({})
    print(f"  Total events: {total}")

    if total > 0:
        sample = events_col().find_one({})
        print(f"  Sample event keys: {list(sample.keys())}")
        print(
            f"  Sample properties: {sample.get('properties', {}).keys() if sample.get('properties') else 'None'}"
        )
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: Test load_events_filtered
print("\n[TEST 2] Testing load_events_filtered...")
try:
    from app.spark.mongo_helpers import load_events_filtered, build_filter_pipeline

    # Try with no filters
    print("  Attempting to load events (no filters, limit 10)...")
    pipeline = build_filter_pipeline()
    print(f"  Empty pipeline: {pipeline}")

    events = load_events_filtered(batch_size=10)
    print(f"  Result: {len(events) if events else 0} events")

    if events and len(events) > 0:
        print(f"  First event keys: {list(events[0].keys())}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback

    traceback.print_exc()

# Test 3: Test SEO load_events_to_spark
print("\n[TEST 3] Testing SEO load_events_to_spark...")
try:
    from app.spark.seo_analytics import load_events_to_spark, get_spark

    spark = get_spark()
    if spark:
        print("  Spark session OK")

        print("  Calling load_events_to_spark(limit=100)...")
        df = load_events_to_spark(spark, limit=100)

        if df:
            count = df.count()
            print(f"  DataFrame count: {count}")
            if count > 0:
                print(f"  Schema: {df.columns}")
        else:
            print("  ERROR: DataFrame is None")
    else:
        print("  ERROR: Spark not available")

except Exception as e:
    print(f"  ERROR: {e}")
    import traceback

    traceback.print_exc()

# Test 4: Test full analyze_traffic_sources
print("\n[TEST 4] Testing analyze_traffic_sources...")
try:
    from app.spark.seo_analytics import analyze_traffic_sources

    print("  Calling analyze_traffic_sources()...")
    result = analyze_traffic_sources()

    if "error" in result:
        print(f"  ERROR: {result['error']}")
    else:
        print(f"  SUCCESS!")
        print(f"  Result keys: {list(result.keys())}")

except Exception as e:
    print(f"  ERROR: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Debug test complete")
print("=" * 60)
