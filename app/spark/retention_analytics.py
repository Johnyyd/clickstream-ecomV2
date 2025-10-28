"""
Spark retention analytics optimized implementation
"""
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from datetime import datetime, timedelta

from app.core.spark import create_spark_session, optimize_spark_df

def analyze_user_retention(events_df, cohort_size=7):
    """
    Analyze user retention patterns with optimized implementation
    
    Args:
        events_df: Spark DataFrame with events
        cohort_size: Size of cohort in days
    """
    # Prepare and optimize events
    events = optimize_spark_df(
        events_df.select(
            "user_id",
            "timestamp",
            F.to_date("timestamp").alias("date")
        )
    )
    
    # Get first activity date for each user
    first_activities = (events
        .groupBy("user_id")
        .agg(F.min("date").alias("first_date"))
        .cache()
    )
    
    # Create cohorts based on first activity
    cohorts = (first_activities
        .withColumn(
            "cohort",
            F.date_trunc("week", "first_date")
        )
        .cache()
    )
    
    # Calculate days between activities
    activity_periods = (events
        .join(cohorts, "user_id")
        .withColumn(
            "days_since_first",
            F.datediff("date", "first_date")
        )
        .withColumn(
            "period",
            F.floor(F.col("days_since_first") / cohort_size)
        )
    )
    
    # Create retention matrix
    retention_matrix = (activity_periods
        .groupBy("cohort")
        .pivot("period")
        .agg(F.countDistinct("user_id"))
        .orderBy("cohort")
        .cache()
    )
    
    # Calculate retention rates
    total_users = first_activities.count()
    retained_users = (events
        .where(F.current_date() >= F.date_add(F.col("date"), cohort_size))
        .select("user_id")
        .distinct()
        .count()
    )
    
    return {
        "cohort_analysis": [
            {
                "cohort_date": str(row["cohort"]),
                "retention": {
                    str(i): row[i] 
                    for i in range(len(row) - 1)
                    if row[i] is not None
                }
            }
            for row in retention_matrix.collect()
        ],
        "retention_metrics": {
            "total_users": total_users,
            "retained_users": retained_users,
            "retention_rate": retained_users / total_users if total_users > 0 else 0,
            "avg_periods": activity_periods.select(
                F.avg("period")
            ).collect()[0][0]
        }
    }