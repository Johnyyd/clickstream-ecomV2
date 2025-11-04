from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
import os
import logging

from pyspark.ml.clustering import KMeans, KMeansModel
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.sql import functions as F

from app.core.spark import spark_manager
from app.core.db_sync import events_col, users_col

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)


def get_spark():
    return spark_manager.get_session()


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load_user_event_df():
    spark = get_spark()
    pipeline = [
        {"$match": {
            "flag.noisy": {"$ne": True},
            "$or": [
                {"properties.source": {"$exists": False}},
                {"properties.source": {"$nin": ["simulation", "basic_sim", "seed_demo"]}}
            ]
        }},
        {"$project": {
            "user_id": 1,
            "session_id": 1,
            "event_type": 1,
            "timestamp": 1,
            "total_amount": {"$ifNull": ["$properties.total_amount", 0]}
        }}
    ]
    events = list(events_col().aggregate(pipeline))
    if not events:
        return None
    rows = []
    for e in events:
        rows.append((
            str(e.get("user_id", "")),
            str(e.get("session_id", "")),
            str(e.get("event_type", "pageview")),
            int(e.get("timestamp") or 0),
            float(e.get("total_amount") or 0.0),
        ))
    df = spark.createDataFrame(rows, ["user_id", "session_id", "event_type", "timestamp", "total_amount"])
    return df


def build_user_features():
    logger.info("[KMeans] Building user features ...")
    spark = get_spark()
    df = _load_user_event_df()
    if df is None:
        return None

    now_ts = int(datetime.now(timezone.utc).timestamp())
    # Per-user aggregates
    agg = df.groupBy("user_id").agg(
        F.countDistinct("session_id").alias("sessions"),
        F.count("*").alias("events"),
        F.sum(F.when(F.col("event_type") == "pageview", 1).otherwise(0)).alias("views"),
        F.sum(F.when(F.col("event_type") == "add_to_cart", 1).otherwise(0)).alias("carts"),
        F.sum(F.when(F.col("event_type") == "checkout", 1).otherwise(0)).alias("checkouts"),
        F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
        F.sum(F.when(F.col("event_type") == "purchase", F.col("total_amount")).otherwise(0.0)).alias("revenue"),
        F.max("timestamp").alias("last_ts"),
    )
    # Derived metrics
    feat = agg.withColumn("aov", F.when(F.col("purchases") > 0, F.col("revenue")/F.col("purchases")).otherwise(F.lit(0.0))) \
             .withColumn("recency_days", (F.lit(now_ts) - F.col("last_ts")) / F.lit(86400.0))

    # Replace nulls
    feat = feat.fillna({"sessions": 0, "events": 0, "views": 0, "carts": 0, "checkouts": 0, "purchases": 0, "revenue": 0.0, "aov": 0.0, "recency_days": 9999.0})

    feature_cols = ["sessions", "events", "views", "carts", "checkouts", "purchases", "revenue", "aov", "recency_days"]
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_raw")
    assembled = assembler.transform(feat)

    scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)
    scaler_model = scaler.fit(assembled)
    scaled = scaler_model.transform(assembled)

    logger.info("[KMeans] Feature DF ready")
    return {
        "data": scaled.select("user_id", "features"),
        "feature_cols": feature_cols,
        "scaler_model": scaler_model,
    }


def train_and_save_kmeans(model_dir: str = "models/kmeans", k: int = 5, max_iter: int = 20, seed: int = 42) -> Dict[str, Any]:
    logger.info("[KMeans] Training KMeans (dir=%s, k=%d)", model_dir, k)
    built = build_user_features()
    if built is None:
        return {"error": "No user events available to build features"}

    data = built["data"]
    scaler_model = built["scaler_model"]
    feature_cols = built["feature_cols"]

    kmeans = KMeans(k=k, seed=seed, maxIter=max_iter, featuresCol="features", predictionCol="segment")
    model: KMeansModel = kmeans.fit(data)
    
    logger.info("[KMeans] Training KMeans model...")
    model_path = _ensure_dir(model_dir)
    logger.info("[KMeans] Saving KMeans model to %s...", model_path)
    model.write().overwrite().save(str(model_path))
    scaler_model.write().overwrite().save(str(model_path / "scaler"))

    with open(model_path / "metadata.json", "w", encoding="utf-8") as f:
        json.dump({"k": k, "feature_cols": feature_cols}, f)

    assigned = model.transform(data).select("user_id", "segment")
    rows = [(r["user_id"], int(r["segment"])) for r in assigned.collect()]

    # Persist assignments onto users collection for fast lookup
    updated = 0
    for uid, seg in rows:
        try:
            users_col().update_one({"_id": __import__("bson").ObjectId(uid)}, {"$set": {"segment": int(seg), "segment_updated_at": datetime.utcnow()}}, upsert=False)
            updated += 1
        except Exception:
            pass
    logger.info("[KMeans] Saved model to %s; segmented %d users", model_path, updated)
    return {"status": "ok", "saved_model_dir": str(model_path), "users_segmented": updated}


def assign_segments_from_saved(model_dir: str = "models/kmeans") -> Dict[str, Any]:
    path = Path(model_dir)
    if not path.exists():
        return {"error": f"Model dir not found: {model_dir}"}

    built = build_user_features()
    if built is None:
        return {"error": "No user events available to build features"}

    data = built["data"]

    try:
        model = KMeansModel.load(str(path))
        assigned = model.transform(data).select("user_id", "segment")
        rows = [(r["user_id"], int(r["segment"])) for r in assigned.collect()]
        updated = 0
        for uid, seg in rows:
            try:
                users_col().update_one({"_id": __import__("bson").ObjectId(uid)}, {"$set": {"segment": int(seg), "segment_updated_at": datetime.utcnow()}}, upsert=False)
                updated += 1
            except Exception:
                pass
        logger.info("[KMeans] Assigned segments for %d users", updated)
        return {"status": "ok", "users_segmented": updated}
    except Exception as e:
        return {"error": str(e)}
