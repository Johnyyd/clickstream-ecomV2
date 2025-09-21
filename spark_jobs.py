# spark_jobs.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, window, to_timestamp, unix_timestamp, collect_set,
    coalesce, lit, current_timestamp, create_map, desc, count,
    size, when
)
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, 
    MapType, DataType, IntegerType
)
import os
from db import events_col
from datetime import datetime
import pytz
import traceback
import gc

# Module-level reusable Spark session
_SPARK_SESSION = None
_SPARK_OWNED = False

def create_spark(app_name="clickstream-analysis", reuse=True):
    """Create or return a reusable SparkSession.

    If reuse=True and a module-level session exists, return it. The session
    will not be stopped by `sessionize_and_counts` to avoid race conditions
    with other threads or the HTTP server.
    """
    global _SPARK_SESSION, _SPARK_OWNED

    # Return existing active session when requested
    if reuse and _SPARK_SESSION is not None:
        return _SPARK_SESSION

    try:
        # Force garbage collection before creating session
        gc.collect()

        spark = SparkSession.builder \
            .appName(app_name) \
            .master("local[*]") \
            .config("spark.sql.execution.pyspark.udf.faulthandler.enabled", "true") \
            .config("spark.python.worker.faulthandler.enabled", "true") \
            .config("spark.driver.memory", "2g") \
            .config("spark.executor.memory", "2g") \
            .config("spark.driver.maxResultSize", "1g") \
            .config("spark.python.worker.memory", "1g") \
            .config("spark.sql.shuffle.partitions", "4") \
            .config("spark.default.parallelism", "4") \
            .config("spark.memory.fraction", "0.8") \
            .config("spark.memory.storageFraction", "0.3") \
            .config("spark.executor.heartbeatInterval", "60s") \
            .config("spark.network.timeout", "1200s") \
            .getOrCreate()

        # Set log level
        spark.sparkContext.setLogLevel("ERROR")

        # Save module-level session so it can be reused by the HTTP server.
        # We intentionally do not mark the session as "owned" here to avoid
        # stopping it from within request handlers. The web server should
        # manage the Spark lifecycle (stop on shutdown) to avoid race
        # conditions that leave py4j/jsc in a None state.
        _SPARK_SESSION = spark
        _SPARK_OWNED = False
        return spark
    except Exception as e:
        print(f"Error creating Spark session: {e}")
        raise

# Define schema for events
events_schema = StructType([
    StructField("_id", StringType(), True),
    StructField("client_id", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("session_id", StringType(), True),
    StructField("timestamp", TimestampType(), True),
    StructField("page", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("properties", MapType(StringType(), StringType()), True)
])

def load_events_as_list(limit=None):
    try:
        q = {}
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
                
                # Handle properties conversion
                properties = d.get("properties", {})
                if isinstance(properties, str):
                    try:
                        import ast
                        properties = ast.literal_eval(properties)
                    except:
                        properties = {}
                elif not isinstance(properties, dict):
                    properties = {}
                
                # Convert MongoDB document to plain Python dict
                event = {
                    "_id": str(d.get("_id", "")),
                    "client_id": str(d.get("client_id", "")),
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
                
        print(f"Loaded {len(docs)} events from MongoDB")
        return docs
    except Exception as e:
        print(f"Error loading events: {e}")
        return []

def sessionize_and_counts(limit=None):
    spark = None
    try:
        print("\n=== Starting Spark Analysis ===")
        spark = create_spark()
        spark.sparkContext.setLogLevel("WARN")
        print("Spark session created successfully")
        
        docs = load_events_as_list(limit=limit)
        print(f"Loaded {len(docs)} documents from MongoDB")
        
        if not docs:
            print("No documents found in MongoDB")
            return {"total_events": 0, "sessions": 0, "top_pages": []}
        
        print("\n=== Processing Data ===")
        # Giảm số lượng cột và đơn giản hóa schema
        simplified_docs = [{
            "session_id": str(d.get("session_id", "")) or "unknown",
            "page": str(d.get("page", "")) or "unknown",
            "timestamp": d.get("timestamp", datetime.now(pytz.UTC))
        } for d in docs]
        
        # Free up memory
        del docs
        print(f"Created {len(simplified_docs)} simplified documents")
        
        # Tạo DataFrame với schema đơn giản hơn
        simple_schema = StructType([
            StructField("session_id", StringType(), True),
            StructField("page", StringType(), True),
            StructField("timestamp", TimestampType(), True)
        ])
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
            df = spark.createDataFrame(valid_docs, schema=simple_schema)
            print(f"Created DataFrame with {df.count()} rows")
        except Exception as e:
            print(f"Error creating DataFrame: {e}")
            return {"total_events": 0, "sessions": 0, "top_pages": [], "funnel_home_to_product": 0}
        
        # Validate DataFrame
        try:
            # Test if DataFrame is valid
            test_count = df.take(1)
            print(f"DataFrame validation successful, sample count: {len(test_count)}")
        except Exception as e:
            print(f"Invalid DataFrame: {e}")
            return {"total_events": 0, "sessions": 0, "top_pages": [], "funnel_home_to_product": 0}
        
        # Optimize the DataFrame
        df = df.repartition(4, "session_id")  # Distribute data by session_id
        df.cache()  # Cache for multiple operations
        
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
            
            # Simplified funnel analysis
            print("\nAnalyzing funnel...")
            try:
                # Get home page sessions
                home_sessions = df.filter(df.page == "/home") \
                    .select("session_id").distinct()
                home_count = home_sessions.count()
                print(f"Sessions with home page: {home_count}")
                
                # Get product page sessions
                product_sessions = df.filter(df.page == "/product") \
                    .select("session_id").distinct()
                product_count = product_sessions.count()
                print(f"Sessions with product page: {product_count}")
                
                # Find sessions that visited both pages
                funnel_home_product = home_sessions.intersect(product_sessions).count()
                print(f"Sessions with both home and product: {funnel_home_product}")
                
            except Exception as e:
                print(f"Error in funnel analysis: {str(e)}")
                traceback.print_exc()
                home_count = 0
                product_count = 0
                funnel_home_product = 0
            
            # Clean up main DataFrame cache
            try:
                df.unpersist()
            except:
                pass
            
            # Return final results
            return {
                "total_events": total,
                "sessions": sessions_count,
                "top_pages": top_pages_list,
                "funnel_home_to_product": funnel_home_product
            }
        except Exception as e:
            print(f"Error calculating metrics: {e}")
            traceback.print_exc()
            # Return using our pre-initialized variables
            return {
                "error": str(e),
                "total_events": total,
                "sessions": sessions_count,
                "top_pages": top_pages_list,
                "funnel_home_to_product": funnel_home_product
            }
        
    except Exception as e:
        print(f"Error in sessionize_and_counts: {str(e)}")
        print("Stack trace:")
        traceback.print_exc()
        # Return with guaranteed initialized values
        return {
            "error": str(e),
            "total_events": 0,
            "sessions": 0,
            "top_pages": [],
            "funnel_home_to_product": 0
        }
    finally:
        # Clean up Spark session and resources
        try:
            if 'df' in locals() and df is not None:
                try:
                    df.unpersist()
                except:
                    pass
            # Only stop the Spark session if this module owns it. When the
            # session is reused across requests (HTTP server), stopping it
            # here can cause PySpark internals to have a None _jsc and raise
            # AttributeError in signal handlers.
            global _SPARK_SESSION, _SPARK_OWNED
            if spark and _SPARK_OWNED:
                try:
                    spark.stop()
                except Exception:
                    pass

            # Force cleanup
            gc.collect()
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")
