import sys
import os
from pathlib import Path
import json
from datetime import datetime
from bson import ObjectId

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.db_sync import users_col, events_col, products_col
from app.spark.session import get_spark
from pyspark.ml.recommendation import ALS
from pyspark.sql import functions as F

def quick_refresh():
    print("Starting quick recommendation refresh...")
    
    spark = get_spark()
    if not spark:
        print("Error: Spark not available")
        return

    print("Loading events...")
    # Load events
    pipeline = [
        {
            "$match": {
                "$or": [
                    {"properties.product_id": {"$exists": True, "$ne": ""}},
                    {"properties.product_ids": {"$exists": True, "$type": "array", "$ne": []}}
                ]
            }
        }
    ]
    events = list(events_col().aggregate(pipeline))
    print(f"Loaded {len(events)} events")
    
    if len(events) < 5:
        print("Not enough events to train model")
        return

    # Prepare interactions
    interactions = []
    user_idx_map = {}
    product_idx_map = {}
    w = {"pageview": 1.0, "add_to_cart": 3.0, "checkout": 4.0, "purchase": 8.0}
    
    def _ensure_maps(uid, pid):
        if uid not in user_idx_map:
            user_idx_map[uid] = len(user_idx_map)
        if pid not in product_idx_map:
            product_idx_map[pid] = len(product_idx_map)

    for e in events:
        uid = str(e.get("user_id"))
        props = e.get("properties", {})
        et = e.get("event_type", "pageview")
        pid = props.get("product_id")
        
        if pid:
            _ensure_maps(uid, pid)
            interactions.append((user_idx_map[uid], product_idx_map[pid], float(w.get(et, 1.0))))
            continue
            
        pids = props.get("product_ids") or []
        if isinstance(pids, list) and pids:
            for p in pids:
                p = str(p)
                _ensure_maps(uid, p)
                interactions.append((user_idx_map[uid], product_idx_map[p], float(w.get("checkout", 4.0))))

    print(f"Created {len(interactions)} interactions")
    
    # Create DataFrame
    df = spark.createDataFrame(interactions, ["user_idx", "product_idx", "rating"])
    df = df.groupBy("user_idx", "product_idx").sum("rating").withColumnRenamed("sum(rating)", "rating")
    
    # Train ALS
    print("Training ALS model...")
    als = ALS(
        maxIter=10, 
        regParam=0.1, 
        userCol="user_idx", 
        itemCol="product_idx", 
        ratingCol="rating", 
        coldStartStrategy="drop", 
        implicitPrefs=False
    )
    model = als.fit(df)
    
    # Generate recommendations for ALL users
    print("Generating recommendations (top 50)...")
    user_recs = model.recommendForAllUsers(50)
    
    # Collect and save
    idx_to_user = {v: k for k, v in user_idx_map.items()}
    idx_to_product = {v: k for k, v in product_idx_map.items()}
    
    rows = user_recs.collect()
    print(f"Generated recommendations for {len(rows)} users")
    
    count = 0
    for row in rows:
        user_idx = int(row["user_idx"])
        user_id = idx_to_user.get(user_idx)
        
        if not user_id:
            continue
            
        items = []
        for rec in row["recommendations"]:
            p_idx = int(rec["product_idx"])
            p_id = idx_to_product.get(p_idx)
            score = float(rec["rating"])
            
            try:
                product = products_col().find_one({"_id": ObjectId(p_id)})
                if product:
                    items.append({
                        "product_id": p_id,
                        "name": product.get("name"),
                        "category": product.get("category"),
                        "price": product.get("price"),
                        "image_url": product.get("image_url"),
                        "predicted_rating": round(score, 2)
                    })
            except Exception:
                pass
        
        if items:
            # Update user document
            try:
                users_col().update_one(
                    {"_id": ObjectId(user_id)},
                    {
                        "$push": {
                            "product_recommendations": {
                                "$each": [{"items": items, "created_at": datetime.utcnow()}],
                                "$slice": -5  # Keep last 5 history entries
                            }
                        }
                    }
                )
                count += 1
            except Exception as e:
                print(f"Error updating user {user_id}: {e}")

    print(f"Successfully updated recommendations for {count} users.")

if __name__ == "__main__":
    quick_refresh()
