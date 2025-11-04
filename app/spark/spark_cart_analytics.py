"""
spark_cart_analytics.py - Cart Abandonment Analysis
Phân tích giỏ hàng bị bỏ rơi, sản phẩm bị abandon nhiều nhất
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

from app.spark.session import get_spark_session
from pyspark.sql.functions import col, explode, split
from app.core.db_sync import carts_col, products_col, users_col
from bson import ObjectId


def get_spark():
    """Get shared Spark session"""
    return get_spark_session()


def analyze_cart_abandonment(username=None):
    """
    Cart Abandonment Analysis
    - Cart abandonment rate
    - Products frequently abandoned
    - Average cart value at abandonment
    """
    try:
        spark = get_spark()
        if spark is None:
            return {"error": "Spark not available. Install Java 8/11 and set JAVA_HOME."}
        
        # Load cart data
        query = {}
        if username:
            user = users_col().find_one({"username": username})
            if user:
                query["user_id"] = user["_id"]
        
        carts = list(carts_col().find(query))
        
        if not carts:
            return {"error": "No cart data available"}
        
        # Process cart data
        cart_data = []
        for cart in carts:
            user_id = str(cart.get("user_id"))
            items = cart.get("items", [])
            
            if not items:
                continue
            
            cart_value = 0
            product_ids = []
            
            for item in items:
                product_id = str(item.get("product_id", ""))
                quantity = int(item.get("quantity", 0))
                
                # Get product price
                try:
                    product = products_col().find_one({"_id": ObjectId(product_id)})
                    if product:
                        price = float(product.get("price", 0))
                        cart_value += price * quantity
                        product_ids.append(product_id)
                except:
                    pass
            
            # Determine if purchased (heuristic: empty cart means purchased)
            purchased = 1 if len(items) == 0 or cart_value == 0 else 0
            
            cart_data.append((
                user_id,
                len(items),
                float(cart_value),
                ",".join(product_ids) if product_ids else "",
                purchased
            ))
        
        if not cart_data:
            return {"error": "No valid cart data"}
        
        df_carts = spark.createDataFrame(cart_data, [
            "user_id", "cart_size", "cart_value", "product_ids", "purchased"
        ])
        
        df_carts.createOrReplaceTempView("carts")
        
        # Calculate abandonment metrics
        abandonment_stats = spark.sql("""
            SELECT 
                COUNT(*) as total_carts,
                SUM(CASE WHEN purchased = 0 THEN 1 ELSE 0 END) as abandoned_carts,
                SUM(CASE WHEN purchased = 1 THEN 1 ELSE 0 END) as completed_carts,
                ROUND(SUM(CASE WHEN purchased = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as abandonment_rate,
                AVG(CASE WHEN purchased = 0 THEN cart_value END) as avg_abandoned_value,
                AVG(CASE WHEN purchased = 1 THEN cart_value END) as avg_completed_value,
                AVG(CASE WHEN purchased = 0 THEN cart_size END) as avg_abandoned_size,
                AVG(CASE WHEN purchased = 1 THEN cart_size END) as avg_completed_size
            FROM carts
        """).collect()[0]
        
        # Most abandoned products
        abandoned_products = spark.sql("""
            SELECT 
                product_id,
                COUNT(*) as abandoned_count
            FROM (
                SELECT explode(split(product_ids, ',')) as product_id
                FROM carts
                WHERE purchased = 0 AND product_ids != ''
            )
            GROUP BY product_id
            ORDER BY abandoned_count DESC
            LIMIT 10
        """).collect()
        
        # Enrich with product details
        abandoned_products_enriched = []
        for row in abandoned_products:
            try:
                product = products_col().find_one({"_id": ObjectId(row["product_id"])})
                if product:
                    abandoned_products_enriched.append({
                        "product_id": row["product_id"],
                        "product_name": product.get("name"),
                        "category": product.get("category"),
                        "price": product.get("price"),
                        "abandoned_count": int(row["abandoned_count"])
                    })
            except:
                pass
        
        return {
            "algorithm": "Cart Abandonment Analysis",
            "total_carts": int(abandonment_stats["total_carts"]),
            "abandoned_carts": int(abandonment_stats["abandoned_carts"]),
            "completed_carts": int(abandonment_stats["completed_carts"]),
            "abandonment_rate": float(abandonment_stats["abandonment_rate"]),
            "avg_abandoned_value": round(float(abandonment_stats["avg_abandoned_value"] or 0), 2),
            "avg_completed_value": round(float(abandonment_stats["avg_completed_value"] or 0), 2),
            "avg_abandoned_size": round(float(abandonment_stats["avg_abandoned_size"] or 0), 2),
            "avg_completed_size": round(float(abandonment_stats["avg_completed_size"] or 0), 2),
            "most_abandoned_products": abandoned_products_enriched
        }
        
    except Exception as e:
        print(f"Error in cart abandonment analysis: {e}")
        traceback.print_exc()
        return {"error": str(e)}
