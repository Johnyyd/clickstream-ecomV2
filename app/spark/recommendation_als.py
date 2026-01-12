"""
spark_recommendation_als.py - Product Recommendation using ALS
Collaborative Filtering để đề xuất sản phẩm cá nhân hóa
"""

import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime

from pyspark.ml.recommendation import ALS, ALSModel
from pyspark.ml.evaluation import RegressionEvaluator
from bson import ObjectId

from app.core.spark import spark_manager
from app.core.db_sync import events_col, products_col, users_col
from app.spark.mongo_helpers import (
    load_events_filtered,
    update_last_processed_timestamp,
)

import logging

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)


def get_spark():
    """Get shared Spark session"""
    return spark_manager.get_session()


def ml_product_recommendations_als(
    username=None,
    top_n=50,
    weights: dict | None = None,
    # Filter parameters
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    segment: str | None = None,
    channel: str | None = None,
):
    """
    Collaborative Filtering using ALS (Alternating Least Squares)
    Generate personalized product recommendations

    Features:
    - User-product interaction matrix
    - Implicit feedback (pageview=1, add_to_cart=3, purchase=5)
    - Top-N recommendations per user
    """
    try:
        logger.info(
            "[ALS] Starting recommendation computation (username=%s, top_n=%s)",
            username,
            top_n,
        )
        spark = get_spark()
        if spark is None:
            return {
                "error": "Spark not available. Install Java 8/11 and set JAVA_HOME.",
                "recommendations": [],
            }

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
                        "Try without username to get recommendations for all users",
                    ],
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

        # Use optimized batch loading with filters
        events = load_events_filtered(
            username=username,
            date_from=date_from,
            date_to=date_to,
            segment=segment,
            channel=channel,
            additional_filters={
                "$or": [
                    {"properties.product_id": {"$exists": True, "$ne": ""}},
                    {
                        "properties.product_ids": {
                            "$exists": True,
                            "$type": "array",
                            "$ne": [],
                        }
                    },
                ]
            },
            batch_size=5000,
        )
        logger.info("[ALS] Loaded events: %d", len(events))

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
                        "Check: python check_als_data.py",
                    ],
                }
            else:
                # No product interactions in entire database
                return {
                    "error": "No product interactions found in database. Events must have 'properties.product_id' field.",
                    "event_count": 0,
                    "suggestions": [
                        "Seed product data: python seed_realistic_data.py",
                        "Check that events contain product_id in properties field",
                        "Verify: python check_als_data.py",
                    ],
                }

        if len(events) < 5:
            return {
                "warning": f"Only {len(events)} product interactions found. ALS works better with more data.",
                "error": "Need at least 5 product interactions for ALS model training",
                "event_count": len(events),
                "suggestions": [
                    "Generate more realistic data with product interactions",
                    "Run: python seed_realistic_data.py",
                ],
            }

        # Create user-product interaction matrix with ratings
        interactions = []
        user_idx_map = {}
        product_idx_map = {}
        # Default implicit feedback weights (can be overridden)
        w = {
            "pageview": 1.0,
            "add_to_cart": 3.0,
            "checkout": 4.0,
            "purchase": 8.0,
        }
        if weights:
            w.update(weights)

        for e in events:
            user_id = str(e.get("user_id"))
            props = e.get("properties", {})
            event_type = e.get("event_type", "pageview")

            def _ensure_maps(pid: str):
                if user_id not in user_idx_map:
                    user_idx_map[user_id] = len(user_idx_map)
                if pid not in product_idx_map:
                    product_idx_map[pid] = len(product_idx_map)

            # Direct product interaction
            product_id = props.get("product_id")
            if product_id:
                _ensure_maps(product_id)
                interactions.append(
                    (
                        user_idx_map[user_id],
                        product_idx_map[product_id],
                        float(w.get(event_type, 1.0)),
                    )
                )
                continue

            # Checkout basket: expand each product_id with checkout weight
            product_ids = props.get("product_ids") or []
            if isinstance(product_ids, list) and product_ids:
                for pid in product_ids:
                    pid = str(pid)
                    _ensure_maps(pid)
                    interactions.append(
                        (
                            user_idx_map[user_id],
                            product_idx_map[pid],
                            float(w.get("checkout", 4.0)),
                        )
                    )

        # Create reverse mappings
        idx_to_user = {v: k for k, v in user_idx_map.items()}
        idx_to_product = {v: k for k, v in product_idx_map.items()}

        # Validate we have enough users and products
        if len(user_idx_map) < 2:
            return {
                "error": "Need at least 2 users for collaborative filtering",
                "user_count": len(user_idx_map),
                "suggestions": [
                    "Generate data with multiple users interacting with products"
                ],
            }

        if len(product_idx_map) < 2:
            return {
                "error": "Need at least 2 products for recommendations",
                "product_count": len(product_idx_map),
                "suggestions": ["Seed more products: python seed_realistic_data.py"],
            }

        # Create DataFrame
        logger.info(
            "[ALS] Building interaction DataFrame with %d rows", len(interactions)
        )
        df = spark.createDataFrame(interactions, ["user_idx", "product_idx", "rating"])

        # Aggregate ratings (sum ratings for same user-product pairs)
        df = (
            df.groupBy("user_idx", "product_idx")
            .sum("rating")
            .withColumnRenamed("sum(rating)", "rating")
        )

        # Cache DataFrame for reuse (avoid recomputation)
        df.cache()

        interaction_count = df.count()
        print(f"Created interaction matrix: {interaction_count} interactions")
        print(f"Users: {len(user_idx_map)}, Products: {len(product_idx_map)}")

        # Final validation
        if interaction_count < 5:
            return {
                "error": f"Insufficient interactions ({interaction_count}) after aggregation",
                "suggestions": ["Generate more user-product interactions"],
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
            implicitPrefs=False,  # Use explicit ratings
        )

        logger.info("[ALS] Training model ...")
        model = als.fit(train_data)

        # Evaluate model
        predictions = model.transform(test_data)
        evaluator = RegressionEvaluator(
            metricName="rmse", labelCol="rating", predictionCol="prediction"
        )
        rmse = evaluator.evaluate(predictions)
        logger.info("[ALS] RMSE=%.4f", rmse)

        # Persist model and mappings for reuse
        try:
            # Resolve models directory at project root to avoid CWD differences
            model_dir = _ensure_dir(_resolve_model_dir("models/als"))
            model.write().overwrite().save(str(model_dir))
            with open(model_dir / "user_idx_map.json", "w", encoding="utf-8") as f:
                json.dump(user_idx_map, f)
            with open(model_dir / "product_idx_map.json", "w", encoding="utf-8") as f:
                json.dump(product_idx_map, f)
            with open(model_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "rmse": float(rmse),
                        "users": len(user_idx_map),
                        "products": len(product_idx_map),
                        "interactions": len(interactions),
                    },
                    f,
                )
            logger.info("[ALS] Model and mappings saved to %s", model_dir)
        except Exception as e:
            logger.warning("[ALS] Failed to persist model: %s", e)

        # Generate top-N recommendations for each user
        logger.info("[ALS] Generating top-%d recommendations for all users", top_n)
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
                        user_recommendations.append(
                            {
                                "product_id": product_id,
                                "product_name": product.get("name"),
                                "category": product.get("category"),
                                "price": product.get("price"),
                                "predicted_rating": round(rating_score, 2),
                                "reason": f"Predicted interest score: {round(rating_score, 2)}",
                            }
                        )
                except:
                    pass

            if user_recommendations:
                recommendations.append(
                    {"user_id": user_id, "recommendations": user_recommendations}
                )

        # If specific username requested, return only their recommendations
        if username:
            user = users_col().find_one({"username": username})
            if user:
                target_user_id = str(user["_id"])
                user_specific = next(
                    (r for r in recommendations if r["user_id"] == target_user_id), None
                )

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
                            "test_samples": test_data.count(),
                        },
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
                "test_samples": test_data.count(),
            },
        }

        # Add admin-specific message
        if is_admin_request:
            result["admin_view"] = True
            result["message"] = (
                f"Admin user '{original_username}' - showing recommendations for ALL {len(recommendations)} users in the system"
            )

        logger.info("[ALS] Finished generating recommendations")

        # Clean up cached DataFrame
        try:
            df.unpersist()
        except:
            pass

        return result

    except Exception as e:
        logger.exception("[ALS] Error in recommendations: %s", e)
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
                    "recommendations_updated_at": ObjectId().generation_time,
                }
            },
        )

        return {"status": "success", "updated": len(recommendations)}

    except Exception as e:
        logger.exception("[ALS] Error updating recommendations: %s", e)
        return {"error": str(e)}


# -------- Model persistence utilities ---------
def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _project_root() -> Path:
    # app/spark/recommendation_als.py -> project root is two levels up from app
    return Path(__file__).resolve().parents[2]


def _resolve_model_dir(model_dir: str | Path) -> Path:
    p = Path(model_dir)
    if p.is_absolute():
        return p
    return _project_root() / p


def train_and_save_als(
    model_dir: str = "models/als",
    username: str | None = None,
    top_n: int = 5,
    weights: dict | None = None,
):
    """
    Train ALS with current data and persist the model and index mappings for fast reuse.
    Returns summary including rmse and paths.
    """
    logger.info("[ALS] Train-and-save initiated (dir=%s)", model_dir)
    res = ml_product_recommendations_als(
        username=username, top_n=top_n, weights=weights
    )
    # Re-train again to get access to df, maps, and model for saving
    try:
        spark = get_spark()
        pipeline = []
        if username:
            user = users_col().find_one({"username": username})
            if user:
                pipeline.append({"$match": {"user_id": user["_id"]}})
        pipeline.extend(
            [
                {
                    "$match": {
                        "$or": [
                            {"properties.product_id": {"$exists": True, "$ne": ""}},
                            {
                                "properties.product_ids": {
                                    "$exists": True,
                                    "$type": "array",
                                    "$ne": [],
                                }
                            },
                        ]
                    }
                }
            ]
        )
        events = list(events_col().aggregate(pipeline))
        if not events:
            return {"error": "No interactions to train"}

        w = {"pageview": 1.0, "add_to_cart": 3.0, "checkout": 4.0, "purchase": 8.0}
        if weights:
            w.update(weights)

        interactions = []
        user_idx_map, product_idx_map = {}, {}

        def _ensure_maps(uid: str, pid: str):
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
                interactions.append(
                    (user_idx_map[uid], product_idx_map[pid], float(w.get(et, 1.0)))
                )
                continue
            pids = props.get("product_ids") or []
            if isinstance(pids, list) and pids:
                for p in pids:
                    p = str(p)
                    _ensure_maps(uid, p)
                    interactions.append(
                        (
                            user_idx_map[uid],
                            product_idx_map[p],
                            float(w.get("checkout", 4.0)),
                        )
                    )

        df = (
            spark.createDataFrame(interactions, ["user_idx", "product_idx", "rating"])
            .groupBy("user_idx", "product_idx")
            .sum("rating")
            .withColumnRenamed("sum(rating)", "rating")
        )
        train_data, test_data = df.randomSplit([0.8, 0.2], seed=42)
        als = ALS(
            maxIter=10,
            regParam=0.1,
            userCol="user_idx",
            itemCol="product_idx",
            ratingCol="rating",
            coldStartStrategy="drop",
            implicitPrefs=False,
        )
        model = als.fit(train_data)
        evaluator = RegressionEvaluator(
            metricName="rmse", labelCol="rating", predictionCol="prediction"
        )
        rmse = float(evaluator.evaluate(model.transform(test_data)))
        logger.info("[ALS] Persisted model RMSE=%.4f", rmse)

        # Save model and mappings
        model_path = _ensure_dir(_resolve_model_dir(model_dir))
        model.write().overwrite().save(str(model_path))
        logger.info("[ALS] Model saved to %s", model_path)
        with open(model_path / "user_idx_map.json", "w", encoding="utf-8") as f:
            json.dump(user_idx_map, f)
        with open(model_path / "product_idx_map.json", "w", encoding="utf-8") as f:
            json.dump(product_idx_map, f)
        with open(model_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "rmse": rmse,
                    "weights": w,
                    "users": len(user_idx_map),
                    "products": len(product_idx_map),
                },
                f,
            )

        res = res or {}
        res.update({"saved_model_dir": str(model_path), "rmse": round(rmse, 4)})
        return res
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


def recommend_from_saved(
    username: str | None = None, top_n: int = 10, model_dir: str = "models/als"
):
    """Load saved ALS model and mappings to generate recommendations quickly."""
    try:
        spark = get_spark()
        model_path = _resolve_model_dir(model_dir)
        if not model_path.exists():
            return {"error": f"Model dir not found: {model_dir}"}
        model = ALSModel.load(str(model_path))
        with open(model_path / "user_idx_map.json", "r", encoding="utf-8") as f:
            user_idx_map = json.load(f)
        with open(model_path / "product_idx_map.json", "r", encoding="utf-8") as f:
            product_idx_map = json.load(f)
        idx_to_user = {int(v): k for k, v in user_idx_map.items()}
        idx_to_product = {int(v): k for k, v in product_idx_map.items()}

        # Build user dataframe
        if username:
            user = users_col().find_one({"username": username})
            if not user:
                return {"error": f"User '{username}' not found"}
            uid = str(user["_id"])
            if uid not in user_idx_map:
                return {
                    "error": f"User '{username}' has no interactions in saved model"
                }
            subset = spark.createDataFrame([(int(user_idx_map[uid]),)], ["user_idx"])
            user_recs_df = model.recommendForUserSubset(subset, top_n)
        else:
            all_users_df = spark.createDataFrame(
                [(i,) for i in idx_to_user.keys()], ["user_idx"]
            )
            user_recs_df = model.recommendForUserSubset(all_users_df, top_n)

        recs = []
        for row in user_recs_df.collect():
            user_idx = int(row["user_idx"])
            u_id = idx_to_user.get(user_idx)
            if not u_id:
                continue
            items = []
            for rec in row["recommendations"]:
                p_idx = (
                    int(rec["product_idx"])
                    if "product_idx" in rec
                    else int(rec[model.itemCol])
                )
                p_id = idx_to_product.get(p_idx)
                score = (
                    float(rec["rating"])
                    if "rating" in rec
                    else float(rec[model.getPredictionCol()])
                )
                try:
                    product = products_col().find_one({"_id": ObjectId(p_id)})
                    if product:
                        items.append(
                            {
                                "product_id": p_id,
                                "product_name": product.get("name"),
                                "category": product.get("category"),
                                "price": product.get("price"),
                                "predicted_rating": round(score, 2),
                            }
                        )
                except Exception:
                    pass
            if items:
                recs.append({"user_id": u_id, "recommendations": items})

        logger.info(
            "[ALS] Generated recommendations from saved model for %d users", len(recs)
        )
        return {
            "algorithm": "ALS Collaborative Filtering (saved)",
            "total_users_with_recs": len(recs),
            "sample_recommendations": recs[:5],
        }
    except Exception as e:
        logger.exception("[ALS] Error generating from saved model: %s", e)
        return {"error": str(e)}


def get_recommendations(username=None, limit=None, top_n=None):
    """Backward-compatible wrapper expected by orchestrator.
    limit is interpreted as desired number of recommendations when top_n is not provided.
    """
    try:
        n = (
            int(top_n)
            if top_n is not None
            else (
                int(limit)
                if isinstance(limit, int)
                or (isinstance(limit, str) and str(limit).isdigit())
                else 10
            )
        )
    except Exception:
        n = 10
    return ml_product_recommendations_als(username=username, top_n=n)
