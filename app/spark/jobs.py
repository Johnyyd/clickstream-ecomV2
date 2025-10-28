# spark_jobs.py
from app.spark.session import get_spark_session
from pyspark.sql.functions import (
    col, window, to_timestamp, unix_timestamp, collect_set,
    coalesce, lit, current_timestamp, create_map, desc, count,
    size, when, expr, first, last, approx_count_distinct, max as max_, min as min_
)
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, 
    MapType, DataType, IntegerType
)
import os
import sys
import json
from db import events_col
from bson import ObjectId
from datetime import datetime
import pytz
import traceback
import gc

def create_spark(app_name="clickstream-analysis", reuse=True):
    """
    Get shared Spark session from centralized manager.
    Legacy function kept for backward compatibility.
    """
    # Use centralized session manager
    return get_spark_session()

# Define schema for events
events_schema = StructType([
    StructField("_id", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("session_id", StringType(), True),
    StructField("timestamp", TimestampType(), True),
    StructField("page", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("properties", MapType(StringType(), StringType()), True)
])

# Define schema for simplified analysis
analysis_schema = StructType([
    StructField("session_id", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("page", StringType(), True),
    StructField("page_base", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("timestamp", TimestampType(), True),
    StructField("properties", MapType(StringType(), StringType()), True)
])

def load_events_as_list(limit=None, user_id=None):
    try:
        q = {}
        if user_id is not None:
            try:
                oid = ObjectId(str(user_id))
                q["$or"] = [{"user_id": oid}, {"user_id": str(user_id)}]
            except Exception:
                q["user_id"] = str(user_id)

        cursor = events_col().find(q).sort("timestamp",1)
        if limit:
            cursor = cursor.limit(limit)
        
        docs = []
        for d in cursor:
            try:
                # Handle timestamp conversion
                timestamp = d.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        # Try parsing the string timestamp
                        timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        try:
                            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            timestamp = datetime.now(pytz.UTC)
                elif not isinstance(timestamp, datetime):
                    timestamp = datetime.now(pytz.UTC)
                # Normalize to UTC naive (no tzinfo)
                try:
                    if getattr(timestamp, 'tzinfo', None) is not None:
                        # convert to UTC then drop tzinfo
                        timestamp = timestamp.astimezone(pytz.UTC).replace(tzinfo=None)
                except Exception:
                    # As a safe fallback use current UTC naive
                    timestamp = datetime.now(pytz.UTC)
                
                # Handle properties conversion
                properties = d.get("properties", {})
                if isinstance(properties, str):
                    try:
                        import ast
                        properties = ast.literal_eval(properties)
                    except:
                        properties = {}
                # After parsing, ensure it's a dict; otherwise default to {}
                if not isinstance(properties, dict):
                    properties = {}
                
                # Convert MongoDB document to plain Python dict
                event = {
                    "_id": str(d.get("_id", "")),
                    "user_id": str(d.get("user_id", "")),
                    "session_id": str(d.get("session_id", "")),
                    "timestamp": timestamp,
                    "page": str(d.get("page", "")),
                    "event_type": str(d.get("event_type", "pageview")),
                    "properties": {str(k): str(v) for k, v in properties.items()}
                }
                docs.append(event)
            except Exception as e:
                print(f"Error processing document: {e}")
                continue
                
        print(f"Loaded {len(docs)} events from MongoDB for user: {str(user_id) if user_id is not None else 'ALL'}")
        return docs
    except Exception as e:
        print(f"Error loading events: {e}")
        return []

def sessionize_and_counts(limit=None, user_id=None):
    """
    Optimized sessionization with DataFrame caching
    """
    spark = None
    cached_df = None
    
    try:
        print("\n=== Starting Optimized Spark Analysis ===")
        from app.spark.session import get_spark_session, cache_dataframe, optimize_dataframe
        
        spark = get_spark_session()
        
        if spark is None:
            print("⚠️ Spark not available - returning empty results")
            return {"total_events": 0, "sessions": 0, "top_pages": [], "error": "Spark not available"}
        
        print("✅ Using shared Spark session")
        
        docs = load_events_as_list(limit=limit, user_id=user_id)
        print(f"Loaded {len(docs)} documents from MongoDB (filtered)")
        
        if not docs:
            print("No documents found in MongoDB")
            return {"total_events": 0, "sessions": 0, "top_pages": []}
        
        print("\n=== Processing Data ===")
        # Process documents with standardized page paths and additional fields
        simplified_docs = []
        for d in docs:
            try:
                page = str(d.get("page", "")).strip()
                # Standardize product pages to /product/{id} format
                if page.startswith("/product/") and "/product/" in page and len(page.split("/")) > 2:
                    # Extract product ID if exists
                    product_id = page.split("/")[2].split("?")[0].strip()
                    if product_id:
                        page = f"/product/{product_id}"
                        page_base = "/product"
                    else:
                        page_base = "/product"
                # Standardize other page paths
                elif page.startswith("/category/"):
                    page_base = "/category"
                elif page.startswith("/search"):
                    page_base = "/search"
                else:
                    page_base = page.split("?")[0]  # Remove query params
                
                # Coerce properties to dict[str, str]
                props = d.get("properties", {})
                if isinstance(props, dict):
                    try:
                        props = {str(k): str(v) for k, v in props.items()}
                    except Exception:
                        props = {}
                else:
                    props = {}
                
                simplified_docs.append({
                    "session_id": str(d.get("session_id", "") or "unknown"),
                    "user_id": str(d.get("user_id", "") or "unknown"),
                    "page": page,
                    "page_base": page_base,
                    "event_type": str(d.get("event_type", "pageview") or "pageview"),
                    "timestamp": d.get("timestamp", datetime.now(pytz.UTC)),
                    "properties": props
                })
            except Exception as e:
                print(f"Error processing document: {e}")
                continue
        
        # Free up memory
        del docs
        print(f"Created {len(simplified_docs)} simplified documents")
        
        # Use the predefined analysis schema
        simple_schema = analysis_schema
        print("Created schema")
        
        # Validate data before creating DataFrame
        print("\nValidating documents...")
        valid_docs = []
        invalid_count = 0
        
        for doc in simplified_docs:
            # Validate timestamp
            if not isinstance(doc["timestamp"], datetime):
                try:
                    doc["timestamp"] = datetime.strptime(str(doc["timestamp"]), "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try:
                        doc["timestamp"] = datetime.strptime(str(doc["timestamp"]), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        invalid_count += 1
                        continue
            valid_docs.append(doc)
        
        print(f"Validated {len(valid_docs)} documents, {invalid_count} invalid")
        
        # Create DataFrame directly with all valid documents
        if not valid_docs:
            print("No valid documents found!")
            return {"total_events": 0, "sessions": 0, "top_pages": [], "funnel_home_to_product": 0}
        
        try:
            print("Creating DataFrame...")
            df = spark.createDataFrame(valid_docs, schema=simple_schema)
            
            # Optimize partitioning
            df = df.coalesce(4)  # Reduce to 4 partitions for better performance
            
            # Cache with optimized storage level
            cached_df = cache_dataframe(df, "MEMORY_AND_DISK")
            df = cached_df
            
            # Trigger caching by counting
            row_count = df.count()
            print(f"✅ Created and cached DataFrame: {row_count} rows")
            
        except Exception as e:
            print(f"Error creating DataFrame: {e}")
            import traceback
            traceback.print_exc()
            return {"total_events": 0, "sessions": 0, "top_pages": [], "funnel_home_to_product": 0}
        
        # Create a view for SQL queries
        df.createOrReplaceTempView("events")
        print("Created temporary view 'events'")
        
        print("\n=== Calculating Metrics ===")
        
        # Initialize result variables
        total = 0
        sessions_count = 0
        top_pages_list = []
        funnel_home_product = 0
        
        try:
            # Get total events count
            try:
                total = df.count()
                print(f"Total events: {total}")
            except Exception as e:
                print(f"Error counting total events: {e}")
                total = 0
            
            # Get unique sessions count
            try:
                sessions_count = df.select("session_id").distinct().count()
                print(f"Unique sessions: {sessions_count}")
            except Exception as e:
                print(f"Error counting unique sessions: {e}")
                sessions_count = 0
            
            # Phân tích pages with optimized memory usage
            print("\nAnalyzing pages...")
            try:
                # Process pages with simple aggregation
                page_counts = df.groupBy("page").agg(
                    count("*").alias("count")
                ).coalesce(1)  # Use single partition for small dataset
                
                # Get and collect top pages in one operation
                try:
                    top_pages = page_counts.orderBy(desc("count")).limit(10).collect()
                    top_pages_list = [{
                        "page": row["page"],
                        "count": int(row["count"])
                    } for row in top_pages]
                    
                    # Show top 5 for verification
                    print("Top 5 pages by count:")
                    for i, page in enumerate(top_pages[:5], 1):
                        print(f"{i}. {page['page']}: {page['count']}")
                        
                except Exception as e:
                    print(f"Error collecting top pages: {e}")
                    top_pages_list = []
                
            except Exception as e:
                print(f"Error analyzing pages: {str(e)}")
                traceback.print_exc()
                top_pages_list = []
            
            print(f"\nFound {len(top_pages_list)} top pages")
            
            # Enhanced funnel analysis with multiple steps
            print("\nAnalyzing funnel...")
            funnel_metrics = {}
            conversion_rates = {}
            
            try:
                # Define funnel steps with their conditions
                funnel_steps = [
                    ("home_visit", "page_base = '/home'"),
                    ("category_view", "page_base = '/category' OR page_base = '/search'"),
                    ("product_view", "page_base = '/product' OR page LIKE '/product/%'"),
                    ("add_to_cart", "event_type = 'add_to_cart' OR page_base = '/cart'"),
                    ("checkout_start", "page_base = '/checkout' OR event_type = 'checkout_start'"),
                    ("purchase", "event_type = 'purchase'")
                ]
                
                # Calculate funnel metrics using SQL for better readability
                for i, (step_name, condition) in enumerate(funnel_steps):
                    # For the first step, just count distinct sessions
                    if i == 0:
                        query = f"""
                            SELECT COUNT(DISTINCT session_id) as count
                            FROM events
                            WHERE {condition}
                        """
                    else:
                        # For subsequent steps, only count sessions that completed previous steps
                        prev_conditions = " AND ".join([f"s{i+1}.session_id IS NOT NULL" for i in range(i)])
                        query = f"""
                            SELECT COUNT(DISTINCT s{i+1}.session_id) as count
                            FROM events s{i+1}
                            INNER JOIN (
                                SELECT DISTINCT session_id
                                FROM events
                                WHERE {funnel_steps[0][1]}
                            ) s1 ON s1.session_id = s{i+1}.session_id
                        """
                        
                        # Add joins for all previous steps
                        for j in range(1, i):
                            query += f"""
                                INNER JOIN (
                                    SELECT DISTINCT session_id
                                    FROM events
                                    WHERE {funnel_steps[j][1]}
                                ) s{j+1} ON s{j+1}.session_id = s{i+1}.session_id
                            """
                        
                        # Add condition for current step
                        query += f"""
                            WHERE {condition}
                        """
                        
                        # Add conditions to ensure steps happen in order
                        if i > 0:
                            for j in range(i):
                                query += f"""
                                    AND EXISTS (
                                        SELECT 1
                                        FROM events prev
                                        WHERE prev.session_id = s{i+1}.session_id
                                        AND prev.timestamp < s{i+1}.timestamp
                                        AND {funnel_steps[j][1]}
                                    )
                                """
                    
                    # Execute query and store result
                    result = spark.sql(query).collect()[0][0]
                    funnel_metrics[step_name] = result
                    print(f"{step_name}: {result} sessions")
                
                # Calculate conversion rates between steps
                for i in range(1, len(funnel_steps)):
                    prev_step = funnel_steps[i-1][0]
                    curr_step = funnel_steps[i][0]
                    if funnel_metrics.get(prev_step, 0) > 0:
                        rate = (funnel_metrics.get(curr_step, 0) / funnel_metrics[prev_step]) * 100
                        conversion_rates[f"{prev_step}_to_{curr_step}"] = f"{rate:.1f}%"
                
                print("\nConversion rates between steps:")
                for step, rate in conversion_rates.items():
                    print(f"{step}: {rate}")
                
                # Store funnel metrics in the result
                funnel_home_product = funnel_metrics.get('product_view', 0)
                
            except Exception as e:
                print(f"Error in funnel analysis: {str(e)}")
                traceback.print_exc()
                funnel_metrics = {}
                conversion_rates = {}
                funnel_home_product = 0
            
            # Clean up main DataFrame cache
            try:
                df.unpersist()
            except:
                pass
            
            # Enhanced session metrics using SQL
            print("\nCalculating session metrics...")
            session_metrics = {}
            try:
                # Session duration and events per session
                session_stats = spark.sql("""
                    SELECT 
                        COUNT(*) as total_events,
                        COUNT(DISTINCT session_id) as total_sessions,
                        COUNT(DISTINCT user_id) as total_users,
                        AVG(events_per_session) as avg_events_per_session,
                        MAX(events_per_session) as max_events_per_session,
                        PERCENTILE(CAST(events_per_session AS DOUBLE), 0.5) as median_events_per_session,
                        AVG(session_duration_seconds) as avg_session_duration_seconds,
                        MAX(session_duration_seconds) as max_session_duration_seconds,
                        PERCENTILE(CAST(session_duration_seconds AS DOUBLE), 0.5) as median_session_duration_seconds,
                        SUM(CASE WHEN events_per_session = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(DISTINCT session_id) as bounce_rate
                    FROM (
                        SELECT 
                            session_id,
                            user_id,
                            COUNT(*) as events_per_session,
                            (UNIX_TIMESTAMP(MAX(timestamp)) - UNIX_TIMESTAMP(MIN(timestamp))) as session_duration_seconds
                        FROM events
                        GROUP BY session_id, user_id
                    ) session_metrics
                """).collect()[0]

                session_metrics = {
                    "total_events": session_stats["total_events"],
                    "total_sessions": session_stats["total_sessions"],
                    "total_users": session_stats["total_users"],
                    "avg_events_per_session": round(session_stats["avg_events_per_session"], 2),
                    "max_events_per_session": session_stats["max_events_per_session"],
                    "median_events_per_session": round(session_stats["median_events_per_session"], 2),
                    "avg_session_duration_seconds": round(session_stats["avg_session_duration_seconds"], 2),
                    "max_session_duration_seconds": session_stats["max_session_duration_seconds"],
                    "median_session_duration_seconds": round(session_stats["median_session_duration_seconds"], 2),
                    "bounce_rate": round(session_stats["bounce_rate"], 4)
                }
                
                print("\nSession Metrics:")
                for k, v in session_metrics.items():
                    print(f"{k}: {v}")
                    
            except Exception as e:
                print(f"Error calculating session metrics: {str(e)}")
                traceback.print_exc()
            
            # Return final results with enhanced metrics
            return {
                "total_events": total,
                "sessions": sessions_count,
                "unique_users": session_metrics.get("total_users", 0),
                "top_pages": top_pages_list,
                "funnel_metrics": funnel_metrics,
                "conversion_rates": conversion_rates,
                "session_metrics": session_metrics,
                "funnel_home_to_product": funnel_home_product
            }
        except Exception as e:
            print(f"Error calculating metrics: {e}")
            traceback.print_exc()
            # Return using our pre-initialized variables with all expected fields
            return {
                "error": str(e),
                "total_events": total,
                "sessions": sessions_count,
                "unique_users": 0,
                "top_pages": top_pages_list,
                "funnel_metrics": funnel_metrics,
                "conversion_rates": conversion_rates,
                "session_metrics": session_metrics,
                "funnel_home_to_product": funnel_home_product
            }
        
    except Exception as e:
        print(f"Error in sessionize_and_counts: {str(e)}")
        print("Stack trace:")
        traceback.print_exc()
        # Return with guaranteed initialized values including all expected fields
        return {
            "error": str(e),
            "total_events": 0,
            "sessions": 0,
            "unique_users": 0,
            "top_pages": [],
            "funnel_metrics": {},
            "conversion_rates": {},
            "session_metrics": {},
            "funnel_home_to_product": 0
        }
    finally:
        # Clean up cached DataFrames (but NOT the shared session)
        try:
            # Unpersist cached DataFrame to free memory
            if cached_df is not None:
                try:
                    cached_df.unpersist()
                    print("✅ Unpersisted cached DataFrame")
                except Exception as e:
                    print(f"Warning unpersisting DataFrame: {e}")
            
            # Clear temp views
            if spark is not None:
                try:
                    spark.catalog.dropTempView("events")
                except:
                    pass
            
            # DO NOT stop shared Spark session - it's reused across requests
            # Force garbage collection
            gc.collect()
            print("✅ Cleanup complete")
            
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")

# if __name__ == "__main__":
#     from pyspark.sql import SparkSession

#     spark = SparkSession.builder \
#         .appName("Clickstream Test") \
#         .master("local[*]") \
#         .getOrCreate()

#     data = [(1, "test"), (2, "spark"), (3, "clickstream")]
#     df = spark.createDataFrame(data, ["id", "value"])
#     df.show()
#     spark.stop()
