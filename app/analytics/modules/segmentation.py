"""
Customer Segmentation Analytics Module
Uses clustering to identify customer segments
"""
from typing import Dict, Any, Optional
import numpy as np
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator

from app.core.spark import spark_manager
from ..base import AnalyticsModule

class SegmentationAnalytics(AnalyticsModule):
    """Analyzes customer segments using clustering"""
    
    def __init__(self):
        super().__init__("Customer Segmentation", parallel=True)
        
    def run_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """
        Run customer segmentation analysis
        
        Uses:
        - K-means clustering
        - Behavioral features
        - Purchase patterns 
        - Engagement metrics
        """
        spark = spark_manager.session
        
        # Extract customer features
        features_df = spark.sql("""
            WITH user_metrics AS (
                SELECT
                    user_id,
                    -- Activity metrics
                    COUNT(*) as total_events,
                    COUNT(DISTINCT DATE_TRUNC('day', timestamp)) as active_days,
                    COUNT(DISTINCT event_type) as unique_actions,
                    
                    -- Purchase behavior
                    SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as purchases,
                    SUM(CASE 
                        WHEN event_type = 'purchase' 
                        THEN CAST(properties.price AS DECIMAL(10,2))
                        ELSE 0 
                    END) as total_spend,
                    
                    -- Cart behavior
                    SUM(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) as cart_adds,
                    
                    -- Browsing patterns
                    SUM(CASE WHEN event_type = 'page_view' THEN 1 ELSE 0 END) as page_views,
                    COUNT(DISTINCT properties.category) as categories_viewed,
                    
                    -- Time metrics
                    DATEDIFF(MAX(timestamp), MIN(timestamp)) as customer_age_days
                    
                FROM events
                WHERE flag.noisy = false
                AND properties.source NOT IN ('simulation', 'basic_sim', 'seed_demo')
                GROUP BY user_id
                HAVING total_events >= 5
            )
            SELECT
                user_id,
                -- Raw metrics
                total_events,
                active_days,
                unique_actions,
                purchases,
                total_spend,
                cart_adds,
                page_views,
                categories_viewed,
                customer_age_days,
                
                -- Derived metrics
                total_spend / GREATEST(purchases, 1) as avg_order_value,
                purchases / GREATEST(active_days, 1) as purchase_frequency,
                cart_adds / GREATEST(purchases, 1) as cart_abandon_ratio,
                total_events / GREATEST(active_days, 1) as daily_activity,
                categories_viewed / GREATEST(active_days, 1) as category_exploration
            FROM user_metrics
        """)
        
        # Prepare features for clustering
        feature_cols = [
            'total_events', 'active_days', 'unique_actions',
            'purchases', 'total_spend', 'cart_adds', 'page_views',
            'categories_viewed', 'customer_age_days', 'avg_order_value',
            'purchase_frequency', 'cart_abandon_ratio', 'daily_activity',
            'category_exploration'
        ]
        
        assembler = VectorAssembler(
            inputCols=feature_cols,
            outputCol="features"
        )
        
        data = assembler.transform(features_df)
        
        # Find optimal k
        silhouette_scores = []
        k_values = range(2, 7)
        
        for k in k_values:
            kmeans = KMeans(k=k, seed=42)
            model = kmeans.fit(data)
            predictions = model.transform(data)
            
            evaluator = ClusteringEvaluator()
            silhouette = evaluator.evaluate(predictions)
            silhouette_scores.append(silhouette)
            
        optimal_k = k_values[np.argmax(silhouette_scores)]
        
        # Train final model
        kmeans = KMeans(k=optimal_k, seed=42)
        model = kmeans.fit(data)
        predictions = model.transform(data)
        
        # Analyze clusters
        cluster_stats = spark.sql(f"""
            WITH cluster_metrics AS (
                SELECT
                    prediction as cluster_id,
                    COUNT(*) as size,
                    
                    -- Averages
                    AVG(total_events) as avg_events,
                    AVG(active_days) as avg_active_days,
                    AVG(purchases) as avg_purchases,
                    AVG(total_spend) as avg_spend,
                    AVG(cart_adds) as avg_cart_adds,
                    AVG(page_views) as avg_page_views,
                    AVG(categories_viewed) as avg_categories,
                    AVG(customer_age_days) as avg_age_days,
                    
                    -- Segment characteristics
                    AVG(purchase_frequency) as avg_purchase_freq,
                    AVG(cart_abandon_ratio) as avg_abandon_ratio,
                    AVG(daily_activity) as avg_daily_activity
                    
                FROM predictions
                GROUP BY prediction
            )
            SELECT
                cluster_id,
                size,
                CASE
                    WHEN avg_purchase_freq > 0.5 AND avg_spend > 1000 
                    THEN 'High Value'
                    WHEN avg_purchase_freq > 0.2 AND avg_spend > 500
                    THEN 'Regular Buyer'
                    WHEN avg_cart_adds > 10 AND avg_abandon_ratio > 2
                    THEN 'Browser'
                    WHEN avg_daily_activity > 5 AND avg_categories > 3
                    THEN 'Active Explorer'
                    ELSE 'Occasional Visitor'
                END as segment_label,
                *
            FROM cluster_metrics
            ORDER BY size DESC
        """)
        
        if username:
            # Get segment for specific user
            user_segment = spark.sql(f"""
                SELECT
                    p.user_id,
                    p.prediction as cluster_id,
                    cm.segment_label,
                    p.total_events,
                    p.active_days,
                    p.purchases,
                    p.total_spend,
                    p.avg_order_value,
                    p.purchase_frequency
                FROM predictions p
                JOIN cluster_metrics cm ON p.prediction = cm.cluster_id
                WHERE p.user_id = '{username}'
            """)
        else:
            user_segment = None
            
        return {
            "optimal_k": optimal_k,
            "silhouette_scores": dict(zip(k_values, silhouette_scores)),
            "cluster_stats": cluster_stats.toPandas().to_dict('records'),
            "user_segment": user_segment.toPandas().to_dict('records')[0] if user_segment else None
        }