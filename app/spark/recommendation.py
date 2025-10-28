"""
Spark ML recommendation engine
"""
from pyspark.ml.recommendation import ALS
from pyspark.sql import functions as F
from pyspark.ml.evaluation import RegressionEvaluator

from app.core.spark import create_spark_session, optimize_spark_df

class RecommendationEngine:
    def __init__(self, spark_session=None):
        """Initialize recommendation engine"""
        self.spark = spark_session or create_spark_session("recommendations")
        self.model = None
        
    def prepare_training_data(self, events_df):
        """
        Prepare event data for training
        """
        # Extract user-item interactions
        interactions = (events_df
            .filter(F.col("event_type").isin(
                ["view_product", "add_to_cart", "purchase"]
            ))
            .select(
                F.col("user_id"),
                F.col("properties.product_id").alias("product_id"),
                F.when(F.col("event_type") == "purchase", 5.0)
                 .when(F.col("event_type") == "add_to_cart", 3.0)
                 .when(F.col("event_type") == "view_product", 1.0)
                 .alias("rating")
            )
            .groupBy("user_id", "product_id")
            .agg(F.max("rating").alias("rating"))
        )
        
        return optimize_spark_df(interactions)
        
    def train_model(self, training_data, **params):
        """
        Train ALS model with optimized parameters
        """
        als = ALS(
            maxIter=10,
            regParam=0.01,
            userCol="user_id",
            itemCol="product_id",
            ratingCol="rating",
            coldStartStrategy="drop",
            **params
        )
        
        # Split data
        train, test = training_data.randomSplit([0.8, 0.2])
        
        # Train model
        self.model = als.fit(train)
        
        # Evaluate
        predictions = self.model.transform(test)
        evaluator = RegressionEvaluator(
            metricName="rmse",
            labelCol="rating",
            predictionCol="prediction"
        )
        rmse = evaluator.evaluate(predictions)
        
        return {
            "rmse": rmse,
            "training_size": train.count(),
            "test_size": test.count()
        }
        
    def get_user_recommendations(self, user_id, n=10):
        """
        Get top N recommendations for user
        """
        if not self.model:
            raise ValueError("Model not trained")
            
        # Get user recommendations
        user_recs = (self.model
            .recommendForUserSubset(
                self.spark.createDataFrame([(user_id,)], ["user_id"]),
                n
            )
            .select(
                F.explode("recommendations").alias("rec")
            )
            .select(
                F.col("rec.product_id"),
                F.col("rec.rating").alias("score")
            )
        )
        
        return [
            {"product_id": row["product_id"], "score": row["score"]}
            for row in user_recs.collect()
        ]
        
    def get_similar_products(self, product_id, n=10):
        """
        Get N most similar products
        """
        if not self.model:
            raise ValueError("Model not trained")
            
        # Get similar items
        item_factors = self.model.itemFactors
        target_factor = (item_factors
            .filter(F.col("id") == product_id)
            .select("features")
            .collect()[0]["features"]
        )
        
        # Calculate similarity
        similar_items = (item_factors
            .filter(F.col("id") != product_id)
            .select(
                "id",
                F.dot("features", F.lit(target_factor)).alias("similarity")
            )
            .orderBy(F.desc("similarity"))
            .limit(n)
        )
        
        return [
            {"product_id": row["id"], "similarity": row["similarity"]}
            for row in similar_items.collect()
        ]