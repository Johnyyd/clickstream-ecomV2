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
        target_user_id = None
        is_admin_request = False
        original_username = username
        
        if username:
            user = users_col().find_one({"username": username})
            if not user:
                return {
                    "error": f"User '{username}' not found in database",
                    "suggestions": [
                        "Check username spelling",
                        "List available users: python list_active_users.py",
                        "Try without username to get recommendations for all users"
                    ]
                }
            
            # Check if user is admin - analyze all users instead
            user_role = user.get("role", "user")
            if user_role == "admin":
                print(f"[ALS] User '{username}' is admin - analyzing ALL users instead")
                is_admin_request = True
                # Don't filter by user_id - analyze entire database
                username = None  # Reset to None to trigger all-users mode
                target_user_id = None
            else:
                target_user_id = user["_id"]
                pipeline.append({"$match": {"user_id": user["_id"]}})
        
        pipeline.extend([
            {
                "$match": {
                    "properties.product_id": {"$exists": True, "$ne": ""}
                }
            }
        ])
        
        events = list(events_col().aggregate(pipeline))
        
        # Check if we have enough data
        if len(events) == 0:
            if username:
                # Specific user has no product interactions
                return {
                    "error": f"User '{username}' has no product interactions (pageview/add_to_cart/purchase on product pages)",
                    "event_count": 0,
                    "suggestions": [
                        f"User '{username}' needs to view products, add to cart, or make purchases",
                        "Generate activity: Simulate user browsing products",
                        "Try a different user with product activity",
                        "Check: python check_als_data.py"
                    ]
                }
            else:
                # No product interactions in entire database
                return {
                    "error": "No product interactions found in database. Events must have 'properties.product_id' field.",
                    "event_count": 0,
                    "suggestions": [
                        "Seed product data: python seed_realistic_data.py",
                        "Check that events contain product_id in properties field",
                        "Verify: python check_als_data.py"
                    ]
                }
        
        if len(events) < 5:
            return {
                "warning": f"Only {len(events)} product interactions found. ALS works better with more data.",
                "error": "Need at least 5 product interactions for ALS model training",
                "event_count": len(events),
                "suggestions": [
                    "Generate more realistic data with product interactions",
                    "Run: python seed_realistic_data.py"
                ]
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
        
        # Validate we have enough users and products
        if len(user_idx_map) < 2:
            return {
                "error": "Need at least 2 users for collaborative filtering",
                "user_count": len(user_idx_map),
                "suggestions": ["Generate data with multiple users interacting with products"]
            }
        
        if len(product_idx_map) < 2:
            return {
                "error": "Need at least 2 products for recommendations",
                "product_count": len(product_idx_map),
                "suggestions": ["Seed more products: python seed_realistic_data.py"]
            }
        
        # Create DataFrame
        df = spark.createDataFrame(interactions, ["user_idx", "product_idx", "rating"])
        
        # Aggregate ratings (sum ratings for same user-product pairs)
        df = df.groupBy("user_idx", "product_idx").sum("rating").withColumnRenamed("sum(rating)", "rating")
        
        interaction_count = df.count()
        print(f"Created interaction matrix: {interaction_count} interactions")
        print(f"Users: {len(user_idx_map)}, Products: {len(product_idx_map)}")
        
        # Final validation
        if interaction_count < 5:
            return {
                "error": f"Insufficient interactions ({interaction_count}) after aggregation",
                "suggestions": ["Generate more user-product interactions"]
            }
        
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
        
        result = {
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
        
        # Add admin-specific message
        if is_admin_request:
            result["admin_view"] = True
            result["message"] = f"Admin user '{original_username}' - showing recommendations for ALL {len(recommendations)} users in the system"
        
        return result
        
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
