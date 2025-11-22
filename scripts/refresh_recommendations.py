import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.api.analysis import _run_spark_analytics_async
from app.core.db_sync import analyses_col
from bson import ObjectId
from datetime import datetime

def refresh_recommendations():
    print("Triggering recommendation refresh for ALL users...")
    
    doc = {
        "user_id": None,
        "created_at": datetime.utcnow(),
        "mode": "spark",
        "summary": {
            "status": "stub",
            "message": "Manual refresh triggered"
        },
        "results": {}
    }
    ins = analyses_col().insert_one(doc)
    analysis_id = ins.inserted_id
    
    print(f"Analysis ID: {analysis_id}")
    
    # Run synchronously for the script
    _run_spark_analytics_async(analysis_id, None)
    
    print("Refresh complete.")

if __name__ == "__main__":
    refresh_recommendations()
