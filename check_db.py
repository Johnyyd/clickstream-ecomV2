from db import analyses_col, events_col
from pprint import pprint

print("\n=== Database Status ===")
print(f"Total events: {events_col().count_documents({})}")
print(f"Total analyses: {analyses_col().count_documents({})}")

print("\n=== Recent Analyses ===")
for analysis in analyses_col().find().sort("created_at", -1).limit(3):
    print("\nAnalysis ID:", analysis.get("_id"))
    print("Status:", analysis.get("status"))
    print("Created:", analysis.get("created_at"))
    print("User ID:", analysis.get("user_id"))
    print("Spark Summary:", analysis.get("spark_summary"))
    if "error" in analysis:
        print("Error:", analysis.get("error"))