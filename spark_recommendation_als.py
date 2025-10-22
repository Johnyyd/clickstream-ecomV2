"""
spark_recommendation_als.py - Product Recommendation using ALS
Collaborative Filtering để đề xuất sản phẩm cá nhân hóa
"""

import os
import sys
import traceback

if "JAVA_HOME" not in os.environ:
    os.environ["JAVA_HOME"] = r"C:\LUUDULIEU\APP\JDK\jdk-17.0.12"

os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
python_exe = sys.executable
os.environ["PYSPARK_PYTHON"] = python_exe
os.environ["PYSPARK_DRIVER_PYTHON"] = python_exe

from spark_session import get_spark_session
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from db import events_col, products_col, users_col
from bson import ObjectId


def get_spark():
    """Get shared Spark session"""
    return get_spark_session()


def ml_product_recommendations_als(username=None, top_n=5):
    """
    Collaborative Filtering using ALS (Alternating Least Squares)
    Generate personalized product recommendations
    
    Features:
    - User-product interaction matrix
    - Implicit feedback (pageview=1, add_to_cart=3, purchase=5)
    - Top-N recommendations per user
    """
    try:
        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available. Install Java 8/11 and set JAVA_HOME.", "recommendations": []}
        
        # Load user-product interactions
        pipeline = []
        if username:
            user = users_col().find_one({"username": username})
            if user:
                pipeline.append({"$match": {"user_id": user["_id"]}})
        
        pipeline.extend([
            {
                "$match": {
                    "properties.product_id": {"$exists": True, "$ne": ""}
                }
            }
        ])
        
        events = list(events_col().aggregate(pipeline))
        
        if len(events) < 10:
            return {
                "error": "Need at least 10 product interactions for ALS",
                "event_count": len(events)
            }
        
        # Create user-product interaction matrix with ratings
        interactions = []
        user_idx_map = {}
        product_idx_map = {}
        
        for e in events:
            user_id = str(e.get("user_id"))
            product_id = e.get("properties", {}).get("product_id")
            
            if not product_id:
                continue
            
            # Map user and product to indices
            if user_id not in user_idx_map:
                user_idx_map[user_id] = len(user_idx_map)
            if product_id not in product_idx_map:
                product_idx_map[product_id] = len(product_idx_map)
            
            # Calculate rating based on event type (implicit feedback)
            event_type = e.get("event_type", "pageview")
            if event_type == "purchase":
                rating = 5.0
            elif event_type == "add_to_cart":
                rating = 3.0
            else:
                rating = 1.0
            
            interactions.append((
                user_idx_map[user_id],
                product_idx_map[product_id],
                rating
            ))
        
        # Create reverse mappings
        idx_to_user = {v: k for k, v in user_idx_map.items()}
        idx_to_product = {v: k for k, v in product_idx_map.items()}
        
        # Create DataFrame
        df = spark.createDataFrame(interactions, ["user_idx", "product_idx", "rating"])
        
        # Aggregate ratings (sum ratings for same user-product pairs)
        df = df.groupBy("user_idx", "product_idx").sum("rating").withColumnRenamed("sum(rating)", "rating")
        
        print(f"Created interaction matrix: {df.count()} interactions")
        print(f"Users: {len(user_idx_map)}, Products: {len(product_idx_map)}")
        
        # Split data for evaluation
        train_data, test_data = df.randomSplit([0.8, 0.2], seed=42)
        
        # Train ALS model
        als = ALS(
            maxIter=10,
            regParam=0.1,
            userCol="user_idx",
            itemCol="product_idx",
            ratingCol="rating",
            coldStartStrategy="drop",
            implicitPrefs=False  # Use explicit ratings
        )
        
        model = als.fit(train_data)
        
        # Evaluate model
        predictions = model.transform(test_data)
        evaluator = RegressionEvaluator(
            metricName="rmse",
            labelCol="rating",
            predictionCol="prediction"
        )
        rmse = evaluator.evaluate(predictions)
        
        # Generate top-N recommendations for each user
        user_recs = model.recommendForAllUsers(top_n)
        
        # Collect recommendations
        recommendations = []
        for row in user_recs.collect():
            user_idx = int(row["user_idx"])
            user_id = idx_to_user.get(user_idx)
            
            if not user_id:
                continue
            
            user_recommendations = []
            for rec in row["recommendations"]:
                product_idx = int(rec["product_idx"])
                product_id = idx_to_product.get(product_idx)
                rating_score = float(rec["rating"])
                
                # Get product details
                try:
                    product = products_col().find_one({"_id": ObjectId(product_id)})
                    if product:
                        user_recommendations.append({
                            "product_id": product_id,
                            "product_name": product.get("name"),
                            "category": product.get("category"),
                            "price": product.get("price"),
                            "predicted_rating": round(rating_score, 2),
                            "reason": f"Predicted interest score: {round(rating_score, 2)}"
                        })
                except:
                    pass
            
            if user_recommendations:
                recommendations.append({
                    "user_id": user_id,
                    "recommendations": user_recommendations
                })
        
        # If specific username requested, return only their recommendations
        if username:
            user = users_col().find_one({"username": username})
            if user:
                target_user_id = str(user["_id"])
                user_specific = next((r for r in recommendations if r["user_id"] == target_user_id), None)
                
                if user_specific:
                    return {
                        "algorithm": "ALS Collaborative Filtering",
                        "rmse": round(rmse, 4),
                        "user": username,
                        "recommendations": user_specific["recommendations"],
                        "model_info": {
                            "total_users": len(user_idx_map),
                            "total_products": len(product_idx_map),
                            "total_interactions": len(interactions),
                            "training_samples": train_data.count(),
                            "test_samples": test_data.count()
                        }
                    }
        
        return {
            "algorithm": "ALS Collaborative Filtering",
            "rmse": round(rmse, 4),
            "total_users_with_recs": len(recommendations),
            "sample_recommendations": recommendations[:5],
            "model_info": {
                "total_users": len(user_idx_map),
                "total_products": len(product_idx_map),
                "total_interactions": len(interactions),
                "training_samples": train_data.count(),
                "test_samples": test_data.count()
            }
        }
        
    except Exception as e:
        print(f"Error in ALS recommendations: {e}")
        traceback.print_exc()
        return {"error": str(e)}


def update_user_recommendations(username, recommendations):
    """
    Update user profile with new recommendations
    Save to users.product_recommendations
    """
    try:
        user = users_col().find_one({"username": username})
        if not user:
            return {"error": "User not found"}
        
        users_col().update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "product_recommendations": recommendations,
                    "recommendations_updated_at": ObjectId().generation_time
                }
            }
        )
        
        return {"status": "success", "updated": len(recommendations)}
        
    except Exception as e:
        print(f"Error updating recommendations: {e}")
        return {"error": str(e)}
