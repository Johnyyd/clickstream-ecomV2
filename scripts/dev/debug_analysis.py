# debug_analysis.py - Debug analysis issue
from analysis import run_analysis
from bson import ObjectId
import json

def debug_analysis():
    print("=== Debug Analysis ===")
    
    # Test with a known user ID
    user_id = "68cf83c71e293f2fd9767a59"  # From previous successful test
    
    print(f"Running analysis for user: {user_id}")
    result = run_analysis(user_id, {"limit": 1000})
    
    print(f"Analysis result ID: {result.get('_id')}")
    print(f"Spark summary: {result.get('spark_summary')}")
    
    # Check if we have real data
    spark_summary = result.get('spark_summary', {})
    if spark_summary.get('total_events', 0) > 0:
        print("✅ SUCCESS: Analysis has real data")
    else:
        print("❌ ISSUE: Analysis returned 0 events")

if __name__ == "__main__":
    debug_analysis()
