"""
spark_ml.py - Machine Learning algorithms using PySpark MLlib
"""

import os
import sys
from pathlib import Path

# Use system JAVA_HOME if available, otherwise set a default
if "JAVA_HOME" not in os.environ:
    os.environ["JAVA_HOME"] = r"C:\LUUDULIEU\APP\JDK\jdk-17.0.12"

# PySpark can work without explicit SPARK_HOME/HADOOP_HOME when installed via pip
# Only set if they don't exist (for local development)
os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"

# Use current Python executable
python_exe = sys.executable
os.environ["PYSPARK_PYTHON"] = python_exe
os.environ["PYSPARK_DRIVER_PYTHON"] = python_exe

from app.spark.session import get_spark_session
from pyspark.sql.functions import col, count, avg, sum as spark_sum, when
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.clustering import KMeans, KMeansModel
from pyspark.ml.classification import (
    DecisionTreeClassifier,
    LogisticRegression,
    DecisionTreeClassificationModel,
    LogisticRegressionModel,
)
from pyspark.ml.fpm import FPGrowth, FPGrowthModel
from pyspark.ml.evaluation import ClusteringEvaluator, BinaryClassificationEvaluator
from pyspark.ml.recommendation import ALS
from app.core.db_sync import events_col, sessions_col
from datetime import datetime
import traceback
from bson import ObjectId

def get_spark():
    """Get shared Spark session"""
    return get_spark_session()


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ml_user_segmentation_kmeans(username=None):
    """
    K-Means Clustering: Phân cụm users dựa trên behavior
    
    Features:
    - Total events
    - Total sessions
    - Avg session duration
    - Conversion rate (checkout/total)
    - Cart interaction rate
    """
    try:
        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available. Install Java 8/11 and set JAVA_HOME.", "segments": []}
        
        # Aggregate user behavior from MongoDB
        pipeline = []
        is_admin_request = False
        original_username = username
        
        if username:
            user = events_col().database.users.find_one({"username": username})
            if user:
                # Check if admin - analyze all users instead
                user_role = user.get("role", "user")
                if user_role == "admin":
                    print(f"[K-Means] User '{username}' is admin - analyzing ALL users")
                    is_admin_request = True
                    username = None  # Analyze all users
                else:
                    pipeline.append({"$match": {"user_id": user["_id"]}})
        
        pipeline.extend([
            {
                "$group": {
                    "_id": "$user_id",
                    "total_events": {"$sum": 1},
                    "checkout_events": {
                        "$sum": {"$cond": [{"$eq": ["$event_type", "purchase"]}, 1, 0]}
                    },
                    "cart_events": {
                        "$sum": {"$cond": [{"$eq": ["$event_type", "add_to_cart"]}, 1, 0]}
                    },
                    "sessions": {"$addToSet": "$session_id"}
                }
            }
        ])
        
        user_data = list(events_col().aggregate(pipeline))
        
        if len(user_data) < 2:
            return {
                "error": "Need at least 2 users for clustering",
                "user_count": len(user_data)
            }
        
        # Prepare data for Spark
        spark_data = []
        for u in user_data:
            user_id = str(u["_id"])
            total_events = u["total_events"]
            sessions_count = len(u["sessions"])
            checkout_events = u["checkout_events"]
            cart_events = u["cart_events"]
            
            conversion_rate = checkout_events / total_events if total_events > 0 else 0
            cart_rate = cart_events / total_events if total_events > 0 else 0
            avg_events_per_session = total_events / sessions_count if sessions_count > 0 else 0
            
            spark_data.append((
                user_id,
                float(total_events),
                float(sessions_count),
                float(avg_events_per_session),
                float(conversion_rate),
                float(cart_rate)
            ))
        
        df = spark.createDataFrame(spark_data, [
            "user_id", "total_events", "sessions_count", 
            "avg_events_per_session", "conversion_rate", "cart_rate"
        ])
        
        # Assemble features
        assembler = VectorAssembler(
            inputCols=["total_events", "sessions_count", "avg_events_per_session", 
                      "conversion_rate", "cart_rate"],
            outputCol="features"
        )
        df_features = assembler.transform(df)
        
        # K-Means with k=3 (Low, Medium, High value users)
        model_dir = _ensure_dir("models/kmeans_basic")
        try:
            model = KMeansModel.load(str(model_dir))
        except Exception:
            kmeans = KMeans(k=3, seed=42, featuresCol="features", predictionCol="cluster")
            model = kmeans.fit(df_features)
            # Save for reuse
            model.write().overwrite().save(str(model_dir))
        
        # Predict clusters
        predictions = model.transform(df_features)
        
        # Evaluate
        evaluator = ClusteringEvaluator(featuresCol="features", predictionCol="cluster", metricName="silhouette")
        silhouette = evaluator.evaluate(predictions)
        
        # Collect results
        results = predictions.select("user_id", "cluster", "total_events", 
                                     "conversion_rate", "cart_rate").collect()
        
        # Aggregate cluster stats
        cluster_stats = predictions.groupBy("cluster").agg(
            count("*").alias("user_count"),
            avg("total_events").alias("avg_events"),
            avg("conversion_rate").alias("avg_conversion"),
            avg("cart_rate").alias("avg_cart_rate")
        ).collect()
        
        # Format results
        clusters = {}
        for stat in cluster_stats:
            cluster_id = int(stat["cluster"])
            clusters[cluster_id] = {
                "user_count": int(stat["user_count"]),
                "avg_events": round(float(stat["avg_events"]), 2),
                "avg_conversion": round(float(stat["avg_conversion"]), 4),
                "avg_cart_rate": round(float(stat["avg_cart_rate"]), 4)
            }
        
        user_clusters = {}
        for row in results:
            user_clusters[row["user_id"]] = {
                "cluster": int(row["cluster"]),
                "total_events": int(row["total_events"]),
                "conversion_rate": round(float(row["conversion_rate"]), 4),
                "cart_rate": round(float(row["cart_rate"]), 4)
            }
        
        result = {
            "algorithm": "K-Means Clustering",
            "silhouette_score": round(silhouette, 4),
            "num_clusters": 3,
            "total_users": len(user_data),
            "cluster_stats": clusters,
            "user_clusters": user_clusters,
            "centers": [center.tolist() for center in model.clusterCenters()]
        }
        
        # Add admin message
        if is_admin_request:
            result["admin_view"] = True
            result["message"] = f"Admin user '{original_username}' - showing segmentation for ALL {len(user_data)} users"
        
        return result
        
    except Exception as e:
        print(f"Error in K-Means clustering: {e}")
        traceback.print_exc()
        return {"error": str(e)}


def ml_conversion_prediction_tree(username=None):
    """
    Decision Tree: Dự đoán conversion (có checkout hay không)
    
    Features:
    - Session duration
    - Number of pages viewed
    - Product views
    - Cart interactions
    """
    try:
        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available. Install Java 8/11 and set JAVA_HOME.", "model_info": {}}
        
        # Get session data
        query = {}
        if username:
            user = sessions_col().database.users.find_one({"username": username})
            if user:
                query["user_id"] = user["_id"]
        
        sessions = list(sessions_col().find(query))
        
        if len(sessions) < 10:
            return {
                "error": "Need at least 10 sessions for training",
                "session_count": len(sessions)
            }
        
        # Prepare data
        spark_data = []
        for session in sessions:
            session_id = session.get("session_id")
            
            # Get events for this session
            events = list(events_col().find({"session_id": session_id}))
            
            if not events:
                continue
            
            # Calculate features
            page_views = len([e for e in events if e.get("event_type") == "pageview"])
            product_views = len([e for e in events if "/p/" in e.get("page", "")])
            cart_adds = len([e for e in events if e.get("event_type") == "add_to_cart"])
            has_purchase = 1.0 if any(e.get("event_type") == "purchase" for e in events) else 0.0
            
            # Session duration (seconds)
            first_event = session.get("first_event_at")
            last_event = session.get("last_event_at")
            if first_event and last_event:
                duration = (last_event - first_event).total_seconds()
            else:
                duration = 0
            
            spark_data.append((
                session_id,
                float(duration),
                float(page_views),
                float(product_views),
                float(cart_adds),
                has_purchase
            ))
        
        if len(spark_data) < 10:
            return {
                "error": "Insufficient data after processing",
                "processed_sessions": len(spark_data)
            }
        
        df = spark.createDataFrame(spark_data, [
            "session_id", "duration", "page_views", 
            "product_views", "cart_adds", "label"
        ])
        
        # Assemble features
        assembler = VectorAssembler(
            inputCols=["duration", "page_views", "product_views", "cart_adds"],
            outputCol="features"
        )
        df_features = assembler.transform(df)
        
        # Split data
        train_data, test_data = df_features.randomSplit([0.7, 0.3], seed=42)
        
        # Train or load Decision Tree
        model_dir = _ensure_dir("models/decision_tree")
        try:
            model = DecisionTreeClassificationModel.load(str(model_dir))
        except Exception:
            dt = DecisionTreeClassifier(
                featuresCol="features",
                labelCol="label",
                maxDepth=5,
                maxBins=32
            )
            model = dt.fit(train_data)
            model.write().overwrite().save(str(model_dir))
        
        # Predict
        predictions = model.transform(test_data)
        
        # Evaluate
        evaluator = BinaryClassificationEvaluator(labelCol="label")
        auc = evaluator.evaluate(predictions)
        
        # Feature importance
        importance = model.featureImportances.toArray()
        feature_names = ["duration", "page_views", "product_views", "cart_adds"]
        feature_importance = {
            name: round(float(imp), 4)
            for name, imp in zip(feature_names, importance)
        }
        
        # Collect some predictions
        sample_predictions = predictions.select(
            "session_id", "label", "prediction", "probability"
        ).limit(10).collect()
        
        samples = []
        for row in sample_predictions:
            samples.append({
                "session_id": row["session_id"][:16] + "...",
                "actual": int(row["label"]),
                "predicted": int(row["prediction"]),
                "confidence": round(float(max(row["probability"])), 4)
            })
        
        return {
            "algorithm": "Decision Tree Classifier",
            "auc_score": round(auc, 4),
            "training_samples": train_data.count(),
            "test_samples": test_data.count(),
            "feature_importance": feature_importance,
            "tree_depth": model.depth,
            "num_nodes": model.numNodes,
            "sample_predictions": samples
        }
        
    except Exception as e:
        print(f"Error in Decision Tree: {e}")
        traceback.print_exc()
        return {"error": str(e)}


def ml_pattern_mining_fpgrowth(username=None, limit=None, **kwargs):
    """
    FP-Growth: Tìm frequent patterns trong page navigation
    
    Finds which pages are frequently visited together
    """
    try:
        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available. Install Java 8/11 and set JAVA_HOME.", "patterns": []}
        
        # Get sessions and their page sequences
        query = {}
        if username:
            user = sessions_col().database.users.find_one({"username": username})
            if user:
                query["user_id"] = user["_id"]
        
        sessions = list(sessions_col().find(query))
        
        if len(sessions) < 5:
            return {
                "error": "Need at least 5 sessions for pattern mining",
                "session_count": len(sessions)
            }
        
        # Prepare transactions (each session is a transaction)
        transactions = []
        for session in sessions:
            session_id = session.get("session_id")
            events = list(events_col().find({"session_id": session_id}).sort("timestamp", 1))
            
            # Get unique pages in this session
            pages = []
            seen = set()
            for e in events:
                page = e.get("page", "")
                # Simplify page URL
                if "/p/" in page:
                    page = "/product"
                elif "/category" in page:
                    page = "/category"
                elif "?" in page:
                    page = page.split("?")[0]
                
                if page and page not in seen:
                    pages.append(page)
                    seen.add(page)
            
            if len(pages) >= 2:  # Need at least 2 items for patterns
                transactions.append((int(session["_id"].generation_time.timestamp()), pages))
        
        if len(transactions) < 5:
            return {
                "error": "Insufficient transactions after processing",
                "transaction_count": len(transactions)
            }
        
        df = spark.createDataFrame(transactions, ["id", "items"])
        
        # FP-Growth (load if available)
        model_dir = _ensure_dir("models/fpgrowth")
        try:
            model = FPGrowthModel.load(str(model_dir))
        except Exception:
            fpGrowth = FPGrowth(
                itemsCol="items",
                minSupport=0.1,  # At least 10% of transactions
                minConfidence=0.3  # At least 30% confidence
            )
            model = fpGrowth.fit(df)
            model.write().overwrite().save(str(model_dir))
        
        # Get frequent itemsets
        freq_itemsets = model.freqItemsets.collect()
        
        # Get association rules
        rules = model.associationRules.collect()
        
        # Format results
        frequent_patterns = []
        for row in freq_itemsets:
            items = list(row["items"])
            freq = int(row["freq"])
            if len(items) >= 2:  # Only multi-item patterns
                frequent_patterns.append({
                    "pattern": items,
                    "frequency": freq,
                    "support": round(freq / len(transactions), 4)
                })
        
        # Sort by frequency
        frequent_patterns.sort(key=lambda x: x["frequency"], reverse=True)
        
        # Format rules
        association_rules = []
        for row in rules[:20]:  # Top 20 rules
            antecedent = list(row["antecedent"])
            consequent = list(row["consequent"])
            confidence = float(row["confidence"])
            lift = float(row["lift"])
            
            association_rules.append({
                "if": antecedent,
                "then": consequent,
                "confidence": round(confidence, 4),
                "lift": round(lift, 4)
            })
        
        # Sort by lift
        association_rules.sort(key=lambda x: x["lift"], reverse=True)
        
        return {
            "algorithm": "FP-Growth Pattern Mining",
            "total_transactions": len(transactions),
            "min_support": 0.1,
            "min_confidence": 0.3,
            "num_frequent_patterns": len(freq_itemsets),
            "num_rules": len(rules),
            "top_patterns": frequent_patterns[:15],
            "top_rules": association_rules[:10]
        }
        
    except Exception as e:
        print(f"Error in FP-Growth: {e}")
        traceback.print_exc()
        return {"error": str(e)}


def ml_purchase_prediction_logistic(username=None):
    """
    Logistic Regression: Dự đoán xác suất purchase
    
    Features:
    - Session duration
    - Page views
    - Product views
    - Cart adds
    - Previous purchases (has history)
    """
    try:
        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available. Install Java 8/11 and set JAVA_HOME.", "predictions": []}
        
        # Get user behavior
        query = {}
        if username:
            user = sessions_col().database.users.find_one({"username": username})
            if user:
                query["user_id"] = user["_id"]
        
        sessions = list(sessions_col().find(query))
        
        if len(sessions) < 20:
            return {
                "error": "Need at least 20 sessions for logistic regression",
                "session_count": len(sessions)
            }
        
        # Prepare data
        spark_data = []
        user_purchase_history = {}  # Track purchase history per user
        
        for session in sessions:
            session_id = session.get("session_id")
            user_id = str(session.get("user_id"))
            
            # Get events
            events = list(events_col().find({"session_id": session_id}).sort("timestamp", 1))
            
            if not events:
                continue
            
            # Features
            page_views = len([e for e in events if e.get("event_type") == "pageview"])
            product_views = len([e for e in events if "/p/" in e.get("page", "")])
            cart_adds = len([e for e in events if e.get("event_type") == "add_to_cart"])
            has_purchase = 1.0 if any(e.get("event_type") == "purchase" for e in events) else 0.0
            
            # Session duration
            first_event = session.get("first_event_at")
            last_event = session.get("last_event_at")
            if first_event and last_event:
                duration = (last_event - first_event).total_seconds()
            else:
                duration = 0
            
            # Has previous purchase
            has_history = 1.0 if user_id in user_purchase_history else 0.0
            
            spark_data.append((
                session_id,
                float(duration),
                float(page_views),
                float(product_views),
                float(cart_adds),
                has_history,
                has_purchase
            ))
            
            # Update history
            if has_purchase > 0:
                user_purchase_history[user_id] = True
        
        if len(spark_data) < 20:
            return {
                "error": "Insufficient data after processing",
                "processed_sessions": len(spark_data)
            }
        
        df = spark.createDataFrame(spark_data, [
            "session_id", "duration", "page_views", 
            "product_views", "cart_adds", "has_history", "label"
        ])
        
        # Assemble features
        assembler = VectorAssembler(
            inputCols=["duration", "page_views", "product_views", "cart_adds", "has_history"],
            outputCol="features"
        )
        df_features = assembler.transform(df)
        
        # Split data
        train_data, test_data = df_features.randomSplit([0.7, 0.3], seed=42)
        
        # Train or load Logistic Regression
        model_dir = _ensure_dir("models/logistic_regression")
        try:
            model = LogisticRegressionModel.load(str(model_dir))
        except Exception:
            lr = LogisticRegression(
                featuresCol="features",
                labelCol="label",
                maxIter=100,
                regParam=0.01
            )
            model = lr.fit(train_data)
            model.write().overwrite().save(str(model_dir))
        
        # Predict
        predictions = model.transform(test_data)
        
        # Evaluate
        evaluator = BinaryClassificationEvaluator(labelCol="label")
        auc = evaluator.evaluate(predictions)
        
        # Get coefficients
        coefficients = model.coefficients.toArray()
        feature_names = ["duration", "page_views", "product_views", "cart_adds", "has_history"]
        feature_coefficients = {
            name: round(float(coef), 4)
            for name, coef in zip(feature_names, coefficients)
        }
        
        # Sample predictions
        sample_predictions = predictions.select(
            "session_id", "label", "prediction", "probability"
        ).limit(10).collect()
        
        samples = []
        for row in sample_predictions:
            prob_array = row["probability"]
            purchase_prob = float(prob_array[1])  # Probability of class 1 (purchase)
            
            samples.append({
                "session_id": row["session_id"][:16] + "...",
                "actual": int(row["label"]),
                "predicted": int(row["prediction"]),
                "purchase_probability": round(purchase_prob, 4)
            })
        
        return {
            "algorithm": "Logistic Regression",
            "auc_score": round(auc, 4),
            "training_samples": train_data.count(),
            "test_samples": test_data.count(),
            "feature_coefficients": feature_coefficients,
            "intercept": round(float(model.intercept), 4),
            "sample_predictions": samples
        }
        
    except Exception as e:
        print(f"Error in Logistic Regression: {e}")
        traceback.print_exc()
        return {"error": str(e)}


# Backward-compatible aliases for orchestrator imports
def ml_kmeans_clustering(username=None, limit=None, **kwargs):
    """Alias to maintain compatibility with orchestrator import name.
    Accepts and ignores 'limit' and extra kwargs.
    """
    return ml_user_segmentation_kmeans(username)


def ml_decision_tree(username=None, limit=None, **kwargs):
    """Alias to maintain compatibility with orchestrator import name.
    Accepts and ignores 'limit' and extra kwargs.
    """
    return ml_conversion_prediction_tree(username)
