"""
Product Recommendation Analytics Module
Provides personalized product recommendations using ALS
"""
from typing import Dict, Any, Optional
import numpy as np
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

from app.core.spark import spark_manager
from ..base import AnalyticsModule

class RecommendationAnalytics(AnalyticsModule):
    """Product recommendations using Alternating Least Squares"""
    
    def __init__(self):
        super().__init__("Product Recommendations", parallel=True)
        
    def run_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """
        Generate product recommendations
        
        Uses:
        - ALS collaborative filtering
        - View/purchase history
        - Product similarity
        - Rating predictions
        """
        spark = spark_manager.session
        
        # Prepare ratings data
        ratings_df = spark.sql("""
            WITH user_product_interactions AS (
                SELECT
                    user_id,
                    properties.product_id,
                    COUNT(*) as view_count,
                    SUM(CASE 
                        WHEN event_type = 'purchase' THEN 3
                        WHEN event_type = 'add_to_cart' THEN 2  
                        ELSE 1
                    END) as implicit_rating
                FROM events
                WHERE flag.noisy = false
                AND properties.source NOT IN ('simulation', 'basic_sim', 'seed_demo')
                AND properties.product_id IS NOT NULL
                GROUP BY user_id, properties.product_id
            )
            SELECT
                -- Hash strings to integers for ALS
                ABS(HASH(user_id)) % 100000000 as user_idx,
                ABS(HASH(product_id)) % 100000000 as item_idx,
                CASE
                    WHEN implicit_rating > 10 THEN 5.0
                    ELSE ROUND(implicit_rating * 5.0 / 10, 1)
                END as rating,
                user_id,
                product_id,
                view_count
            FROM user_product_interactions
        """)
        
        # Split into train/test
        (train_df, test_df) = ratings_df.randomSplit([0.8, 0.2])
        
        # Build ALS model
        als = ALS(
            maxIter=10,
            regParam=0.1,
            userCol="user_idx",
            itemCol="item_idx",
            ratingCol="rating",
            coldStartStrategy="drop"
        )
        
        model = als.fit(train_df)
        
        # Get RMSE on test set
        predictions = model.transform(test_df)
        evaluator = RegressionEvaluator(
            metricName="rmse",
            labelCol="rating",
            predictionCol="prediction"
        )
        rmse = evaluator.evaluate(predictions)
        
        # Generate recommendations
        if username:
            # Get recommendations for specific user
            user_idx = abs(hash(username)) % 100000000
            user_recs = model.recommendForUserSubset(
                spark.createDataFrame([(user_idx,)], ["user_idx"]),
                10
            )
            
            # Get product details
            product_df = spark.sql("""
                SELECT 
                    ABS(HASH(product_id)) % 100000000 as item_idx,
                    product_id,
                    name,
                    category,
                    price
                FROM products
            """)
            
            # Join recommendations with product details
            recs_with_details = spark.sql("""
                SELECT
                    r.product_id,
                    p.name,
                    p.category,
                    p.price,
                    r.rating as predicted_rating
                FROM (
                    SELECT 
                        recommendations.item_idx,
                        FIRST(products.product_id) as product_id,
                        FIRST(recommendations.rating) as rating
                    FROM (
                        SELECT 
                            item_idx,
                            rating 
                        FROM UNNEST(
                            (SELECT recommendations.r.item_idx, recommendations.r.rating 
                             FROM user_recs 
                             LATERAL VIEW EXPLODE(recommendations) r)
                        )
                    ) recommendations
                    JOIN products 
                    ON ABS(HASH(products.product_id)) % 100000000 = recommendations.item_idx
                    GROUP BY recommendations.item_idx
                ) r
                JOIN products p ON r.product_id = p.product_id
                ORDER BY r.rating DESC
            """)
            
            recommendations = recs_with_details.toPandas().to_dict('records')
            
        else:
            # Get general popular items
            recommendations = spark.sql("""
                SELECT
                    p.product_id,
                    p.name,
                    p.category,
                    p.price,
                    COUNT(*) as view_count,
                    COUNT(DISTINCT e.user_id) as unique_viewers
                FROM products p
                JOIN events e ON p.product_id = e.properties.product_id
                WHERE e.flag.noisy = false
                GROUP BY p.product_id, p.name, p.category, p.price
                ORDER BY unique_viewers DESC
                LIMIT 10
            """).toPandas().to_dict('records')
        
        # Get model stats
        stats_df = spark.sql("""
            SELECT
                COUNT(DISTINCT user_idx) as total_users,
                COUNT(DISTINCT item_idx) as total_items,
                COUNT(*) as total_interactions,
                AVG(rating) as avg_rating
            FROM ratings_df
        """)
        
        model_stats = stats_df.toPandas().to_dict('records')[0]
        
        return {
            "recommendations": recommendations,
            "model_stats": {
                **model_stats,
                "rmse": rmse
            }
        }