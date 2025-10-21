"""
spark_retention_analytics.py - Cohort & Retention Analysis
Phân tích retention theo cohort, churn rate
"""

import os
import sys
import traceback
from datetime import datetime

if "JAVA_HOME" not in os.environ:
    os.environ["JAVA_HOME"] = r"C:\LUUDULIEU\APP\JDK\jdk-17.0.12"

os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
python_exe = sys.executable
os.environ["PYSPARK_PYTHON"] = python_exe
os.environ["PYSPARK_DRIVER_PYTHON"] = python_exe

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, countDistinct, datediff, current_date
from db import users_col, events_col
from bson import ObjectId


def get_spark():
    """Get or create Spark session"""
    existing = SparkSession._instantiatedSession
    if existing is not None:
        return existing
    
    return SparkSession.builder \
        .appName("Retention-Analytics") \
        .master("local[*]") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.sql.adaptive.enabled", "false") \
        .config("spark.ui.enabled", "false") \
        .config("spark.driver.host", "localhost") \
        .config("spark.driver.bindAddress", "127.0.0.1") \
        .getOrCreate()


def load_events_to_spark(spark, username=None):
    """Load events from MongoDB"""
    try:
        pipeline = []
        if username:
            user = users_col().find_one({"username": username})
            if user:
                pipeline.append({"$match": {"user_id": user["_id"]}})
        
        pipeline.append({
            "$match": {
                "flag.noisy": {"$ne": True},
                "$or": [
                    {"properties.source": {"$exists": False}},
                    {"properties.source": {"$nin": ["simulation", "basic_sim", "seed_demo"]}}
                ]
            }
        })
        
        events = list(events_col().aggregate(pipeline))
        
        if not events:
            return None
        
        spark_data = []
        for e in events:
            spark_data.append((
                str(e.get("user_id", "")),
                str(e.get("session_id", "")),
                e.get("timestamp"),
                str(e.get("event_type", "pageview"))
            ))
        
        df = spark.createDataFrame(spark_data, ["user_id", "session_id", "timestamp", "event_type"])
        return df
        
    except Exception as e:
        print(f"Error loading events: {e}")
        return None


def analyze_cohort_retention(username=None):
    """
    Cohort & Retention Analysis
    - User cohorts by signup date
    - Retention rate over time
    - User segments by activity
    """
    try:
        spark = get_spark()
        
        # Load user data
        query = {}
        if username:
            user = users_col().find_one({"username": username})
            if user:
                query["_id"] = user["_id"]
        
        users = list(users_col().find(query, {"_id": 1, "created_at": 1}))
        
        if not users:
            return {"error": "No user data available"}
        
        # Load events
        df_events = load_events_to_spark(spark, username=username)
        if df_events is None:
            return {"error": "No event data available"}
        
        df_events.createOrReplaceTempView("events")
        
        # Create user cohorts
        user_data = []
        for user in users:
            user_id = str(user["_id"])
            created_at = user.get("created_at")
            if not created_at:
                continue
            
            cohort_date = created_at.strftime("%Y-%m-%d") if isinstance(created_at, datetime) else str(created_at)[:10]
            
            user_data.append((
                user_id,
                cohort_date,
                created_at
            ))
        
        if not user_data:
            return {"error": "No valid user data with signup dates"}
        
        df_users = spark.createDataFrame(user_data, ["user_id", "cohort_date", "signup_timestamp"])
        df_users.createOrReplaceTempView("users")
        
        # Calculate retention
        retention_data = spark.sql("""
            SELECT 
                u.cohort_date,
                COUNT(DISTINCT u.user_id) as cohort_size,
                COUNT(DISTINCT CASE 
                    WHEN DATEDIFF(DATE(e.timestamp), DATE(u.signup_timestamp)) BETWEEN 1 AND 7 
                    THEN e.user_id 
                END) as retained_week1,
                COUNT(DISTINCT CASE 
                    WHEN DATEDIFF(DATE(e.timestamp), DATE(u.signup_timestamp)) BETWEEN 8 AND 14 
                    THEN e.user_id 
                END) as retained_week2,
                COUNT(DISTINCT CASE 
                    WHEN DATEDIFF(DATE(e.timestamp), DATE(u.signup_timestamp)) BETWEEN 15 AND 30 
                    THEN e.user_id 
                END) as retained_month1
            FROM users u
            LEFT JOIN events e ON u.user_id = e.user_id
            GROUP BY u.cohort_date
            ORDER BY u.cohort_date DESC
            LIMIT 10
        """).collect()
        
        cohorts = []
        for row in retention_data:
            cohort_size = int(row["cohort_size"])
            if cohort_size > 0:
                cohorts.append({
                    "cohort_date": row["cohort_date"],
                    "cohort_size": cohort_size,
                    "retention_week1": round(int(row["retained_week1"]) / cohort_size * 100, 2),
                    "retention_week2": round(int(row["retained_week2"]) / cohort_size * 100, 2),
                    "retention_month1": round(int(row["retained_month1"]) / cohort_size * 100, 2)
                })
        
        # Calculate average retention
        avg_retention = {
            "week1": round(sum(c["retention_week1"] for c in cohorts) / len(cohorts), 2) if cohorts else 0,
            "week2": round(sum(c["retention_week2"] for c in cohorts) / len(cohorts), 2) if cohorts else 0,
            "month1": round(sum(c["retention_month1"] for c in cohorts) / len(cohorts), 2) if cohorts else 0
        }
        
        # User activity segments
        user_segments = spark.sql("""
            SELECT 
                CASE 
                    WHEN days_since_last_activity <= 7 THEN 'Active'
                    WHEN days_since_last_activity <= 30 THEN 'At Risk'
                    ELSE 'Churned'
                END as segment,
                COUNT(*) as user_count
            FROM (
                SELECT 
                    user_id,
                    DATEDIFF(CURRENT_DATE(), MAX(DATE(timestamp))) as days_since_last_activity
                FROM events
                GROUP BY user_id
            )
            GROUP BY segment
        """).collect()
        
        return {
            "algorithm": "Cohort & Retention Analysis",
            "cohorts": cohorts,
            "average_retention": avg_retention,
            "user_segments": [
                {
                    "segment": row["segment"],
                    "user_count": int(row["user_count"])
                }
                for row in user_segments
            ]
        }
        
    except Exception as e:
        print(f"Error in cohort retention analysis: {e}")
        traceback.print_exc()
        return {"error": str(e)}
