"""
Product Affinity Mining using FP-Growth
- Builds frequent itemsets from checkout/purchase baskets
- Generates association rules for product-to-product affinity
- Persists model and provides quick recommendation API from saved rules
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import os
import logging

from pyspark.ml.fpm import FPGrowth, FPGrowthModel
from pyspark.sql import functions as F

from app.core.spark import spark_manager
from app.core.db_sync import events_col, products_col

logger = logging.getLogger(__name__)
if os.getenv("ANALYTICS_VERBOSE", "1") == "1":
    logging.basicConfig(level=logging.INFO)


def get_spark():
    return spark_manager.get_session()


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load_transactions() -> List[List[str]]:
    """
    Build transactions from events:
    - Prefer checkout events (properties.product_ids)
    - Fallback include purchase with single product_id as singleton baskets
    """
    pipeline = [
        {"$match": {
            "$or": [
                {"event_type": "checkout", "properties.product_ids": {"$exists": True, "$type": "array", "$ne": []}},
                {"event_type": "purchase", "properties.product_id": {"$exists": True, "$ne": ""}},
            ]
        }},
        {"$project": {
            "event_type": 1,
            "items": {
                "$cond": [
                    {"$eq": ["$event_type", "checkout"]},
                    "$properties.product_ids",
                    ["$properties.product_id"]
                ]
            }
        }}
    ]
    events = list(events_col().aggregate(pipeline))
    logger.info("[FP] Loaded %d checkout/purchase events for transactions", len(events))
    tx = []
    for e in events:
        items = e.get("items") or []
        items = [str(x) for x in items if x]
        # Deduplicate within a basket
        items = list(dict.fromkeys(items))
        if len(items) >= 2 or e.get("event_type") == "checkout":
            tx.append(items)
        elif len(items) == 1:
            # keep singleton to help support counting but won't create pairs
            tx.append(items)
    logger.info("[FP] Built %d transactions", len(tx))
    return tx


def train_and_save_fpgrowth(model_dir: str = "models/fpgrowth", min_support: float = 0.005, min_confidence: float = 0.2) -> Dict[str, Any]:
    """
    Train FP-Growth on current transactions and persist model and derived rules.
    Returns basic metrics and sample rules.
    """
    logger.info("[FP] Training FP-Growth (dir=%s, min_support=%s, min_conf=%s)", model_dir, min_support, min_confidence)
    spark = get_spark()
    tx = _load_transactions()
    if not tx:
        return {"error": "No transactions found from checkout/purchase events"}

    df = spark.createDataFrame([(t,) for t in tx], ["items"]).withColumn("items", F.expr("filter(items, x -> x is not null)"))

    fp = FPGrowth(itemsCol="items", minSupport=min_support, minConfidence=min_confidence)
    logger.info("[FP] Fitting model on %d transactions", df.count())
    model: FPGrowthModel = fp.fit(df)

    # Persist Spark model and JSON exports for quick serving
    model_path = _ensure_dir(model_dir)
    model.write().overwrite().save(str(model_path))
    logger.info("[FP] Model saved to %s", model_path)

    # Export frequent itemsets and rules to JSON for fast API lookup
    itemsets = [
        {"items": row["items"], "freq": int(row["freq"])}
        for row in model.freqItemsets.collect()
    ]
    rules = [
        {"antecedent": row["antecedent"], "consequent": row["consequent"], "confidence": float(row["confidence"]), "lift": float(row.get("lift", 0.0))}
        for row in model.associationRules.withColumn("lift", (F.col("confidence")/F.lit(1.0))).collect()
    ]

    with open(model_path / "frequent_itemsets.json", "w", encoding="utf-8") as f:
        json.dump(itemsets, f)
    with open(model_path / "association_rules.json", "w", encoding="utf-8") as f:
        json.dump(rules, f)

    logger.info("[FP] Exported %d itemsets and %d rules", len(itemsets), len(rules))
    return {
        "status": "ok",
        "model_dir": str(model_path),
        "transactions": len(tx),
        "itemsets": len(itemsets),
        "rules": len(rules),
        "sample_rules": rules[:10]
    }


def recommend_affinity(product_id: str, top_n: int = 5, model_dir: str = "models/fpgrowth") -> Dict[str, Any]:
    """Recommend related products using saved association rules (antecedent -> consequent)."""
    path = Path(model_dir)
    if not path.exists():
        return {"error": f"Model dir not found: {model_dir}"}
    try:
        with open(path / "association_rules.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
    except Exception as e:
        return {"error": f"Failed to load rules: {e}"}

    # Score candidate consequents by confidence (could combine with lift later)
    candidates: Dict[str, float] = {}
    for r in rules:
        ant = r.get("antecedent") or []
        cons = r.get("consequent") or []
        if len(cons) != 1:
            continue
        if product_id in ant:
            pid = cons[0]
            candidates[pid] = max(candidates.get(pid, 0.0), float(r.get("confidence", 0.0)))

    # Enrich with product metadata
    ranked = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:top_n]
    recs = []
    for pid, score in ranked:
        try:
            p = products_col().find_one({"_id": __import__("bson").ObjectId(pid)})
            if p:
                recs.append({
                    "product_id": pid,
                    "product_name": p.get("name"),
                    "category": p.get("category"),
                    "price": p.get("price"),
                    "score": round(float(score), 3)
                })
        except Exception:
            pass
    logger.info("[FP] Recommended %d related products for %s", len(recs), product_id)
    return {"product_id": product_id, "related_products": recs}


def load_model(model_dir: str = "models/fpgrowth") -> Optional[FPGrowthModel]:
    path = Path(model_dir)
    if not path.exists():
        return None
    try:
        return FPGrowthModel.load(str(path))
    except Exception:
        return None
