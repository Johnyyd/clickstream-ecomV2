"""
Test SEO Analytics Refactor
Quick standalone test for Phase 2.1 proof-of-concept
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

print("=" * 60)
print("SEO Analytics Refactor Test")
print("=" * 60)

# Test new architecture
print("\n[TEST] Running refactored SEO analytics...")
try:
    from app.spark.seo_analytics import analyze_traffic_sources

    # Test with date range (last 30 days)
    date_to = datetime.now()
    date_from = date_to - timedelta(days=30)

    print(f"Date range: {date_from.date()} to {date_to.date()}")
    print("Running analysis...")

    result = analyze_traffic_sources(date_from=date_from, date_to=date_to)

    if "error" in result:
        print(f"\n[FAIL] Error: {result['error']}")
    else:
        print(f"\n[OK] Success!")
        print(f"\nResults:")
        print(f"  - Traffic sources: {len(result.get('traffic_by_source', []))}")
        print(f"  - Landing pages: {len(result.get('landing_pages', []))}")
        print(f"  - Bounce rates: {len(result.get('bounce_rate_by_source', []))}")
        print(f"  - Conversion rates: {len(result.get('conversion_by_source', []))}")

        # Show sample data
        if result.get("traffic_by_source"):
            print(f"\nTop source: {result['traffic_by_source'][0]}")

except Exception as e:
    print(f"\n[FAIL] Exception: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)
