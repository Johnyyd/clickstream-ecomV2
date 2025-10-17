# spark_jobs.py
from pyspark.sql import SparkSession
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
import os
os.environ["JAVA_HOME"] = r"C:\Program Files\Eclipse Adoptium\jdk-21.0.8.9-hotspot"
os.environ["SPARK_HOME"] = r"C:\LUUDULIEU\APP\Spark\Spark\spark-4.0.0"
os.environ["HADOOP_HOME"] = r"C:\LUUDULIEU\APP\Hadoop\hadoop-3.3.4"
os.environ["PATH"] = (
    os.environ["JAVA_HOME"] + r"\bin;" +
    os.environ["SPARK_HOME"] + r"\bin;" +
    os.environ["HADOOP_HOME"] + r"\bin;" +
    os.environ["PATH"]
)
os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
os.environ["PYSPARK_PYTHON"] = r"C:\LUUDULIEU\CODE\github\clickstream-ecomV2\venv\Scripts\python.exe"
os.environ["PYSPARK_DRIVER_PYTHON"] = r"C:\LUUDULIEU\CODE\github\clickstream-ecomV2\venv\Scripts\python.exe"
os.environ["ARROW_PRE_0_15_IPC_FORMAT"] = "1"
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

        conf = None
        
        # Resolve Python executable robustly (avoid Windows Store alias)
        def _resolve_python_exec():
            try:
                import shutil
            except Exception:
                shutil = None
            candidates = [
                os.environ.get("PYSPARK_PYTHON"),
                getattr(sys, "_base_executable", None),
                sys.executable,
                shutil.which("python3") if shutil else None,
                shutil.which("python") if shutil else None,
            ]
            for c in candidates:
                if not c:
                    continue
                # Skip Microsoft Store alias path
                if "WindowsApps" in str(c):
                    continue
                # If c is an absolute path, ensure it exists
                try:
                    if os.path.isabs(c) and not os.path.exists(c):
                        continue
                except Exception:
                    pass
                return c
            return sys.executable

        py_exec = _resolve_python_exec()

        # Ensure PySpark workers use the exact same Python interpreter
        os.environ["PYSPARK_PYTHON"] = py_exec
        os.environ["PYSPARK_DRIVER_PYTHON"] = py_exec
        # Force Spark to use IPv4 localhost
        os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
        os.environ["SPARK_LOCAL_HOSTNAME"] = "localhost"

        print(f"Using Python for Spark: {py_exec}")

        spark = (
            SparkSession.builder
                .appName(app_name)
                .master("local[*]")
                .config("spark.sql.execution.pyspark.udf.faulthandler.enabled", "true")
                .config("spark.python.worker.faulthandler.enabled", "true")
                .config("spark.driver.memory", "6g")
                .config("spark.executor.memory", "6g")
                .config("spark.driver.maxResultSize", "1g")
                .config("spark.python.worker.memory", "1g")
                .config("spark.sql.shuffle.partitions", "1")
                .config("spark.default.parallelism", "1")
                .config("spark.memory.fraction", "0.8")
                .config("spark.memory.storageFraction", "0.3")
                .config("spark.executor.heartbeatInterval", "60s")
                .config("spark.network.timeout", "1200s")
                # Bind explicitly to localhost to avoid Hyper-V/WSL interfaces on Windows
                .config("spark.driver.bindAddress", "127.0.0.1")
                .config("spark.driver.host", "127.0.0.1")
                .config("spark.local.ip", "127.0.0.1")
                .config("spark.blockManager.port", "0")
                .config("spark.port.maxRetries", "50")
                .config("spark.driver.extraJavaOptions", "-Djava.net.preferIPv4Stack=true")
                .config("spark.executor.extraJavaOptions", "-Djava.net.preferIPv4Stack=true")
                .config("spark.python.auth.socketTimeout", "120")
                .config("spark.ui.enabled", "false")
                # Ensure the same Python is used for driver and workers
                .config("spark.pyspark.driver.python", py_exec)
                .config("spark.pyspark.python", py_exec)
                .config("spark.executorEnv.PYSPARK_PYTHON", py_exec)
                # Tắt Hive để tránh gọi constructor lỗi HashMap
                .config("spark.sql.catalogImplementation", "in-memory")
                # Tránh auto load session từ context cũ
                .config("spark.driver.bindAddress", "127.0.0.1")
                .config("spark.driver.host", "127.0.0.1")
                
                .config("spark.executorEnv.PYTHONUNBUFFERED", "1") \
                .config("spark.python.worker.debug", "true")

                .config("spark.executorEnv.PYTHONPATH", os.environ.get("PYTHONPATH", "")) \
                .config("spark.executorEnv.PYSPARK_PYTHON", sys.executable) \
                .config("spark.executorEnv.PYSPARK_DRIVER_PYTHON", sys.executable)
                .config("spark.sql.execution.arrow.pyspark.enabled", "false")

                .config("spark.python.worker.reuse", "true") \
                .config("spark.python.use.daemon", "true") \
                .config("spark.executorEnv.PYSPARK_PYTHON", os.environ["PYSPARK_PYTHON"]) \
                .config("spark.executorEnv.PYSPARK_DRIVER_PYTHON", os.environ["PYSPARK_DRIVER_PYTHON"])

                # Temp dirs (avoid long UNC paths)
                .config("spark.local.dir", os.environ.get("SPARK_LOCAL_DIRS", os.path.join(os.getcwd(), "tmp_spark")))
                # .getOrCreate()
        )
        print(f"Spark PYSPARK_PYTHON = {os.environ.get('PYSPARK_PYTHON')}")
        print(f"Spark PYSPARK_DRIVER_PYTHON = {os.environ.get('PYSPARK_DRIVER_PYTHON')}")
        # Nếu bạn có danh sách cấu hình dạng list, hãy chuyển thành dict trước:
        if isinstance(conf, list):
            conf = dict(conf)

        if isinstance(conf, dict):
            for k, v in conf.items():
                spark = spark.config(k, v)

        spark = spark.getOrCreate()
        
        # Set log level
        spark.sparkContext.setLogLevel("WARN")
        return spark

        # Quick sanity checks to detect worker/env issues early
        try:
            test_rdd = spark.sparkContext.parallelize([1]).map(lambda x: x + 1).collect()
            print(f"Spark worker test OK: {test_rdd}")
            test_df = spark.createDataFrame([{"a": 1}])
            print(f"Spark DataFrame test OK, count: {test_df.count()}")
        except Exception as diag_err:
            print(f"Spark worker/DF diagnostic failed: {diag_err}")
            # Continue; downstream logic will handle and report gracefully

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
                            timestamp = datetime.utcnow()
                elif not isinstance(timestamp, datetime):
                    timestamp = datetime.utcnow()
                # Normalize to UTC naive (no tzinfo)
                try:
                    if getattr(timestamp, 'tzinfo', None) is not None:
                        # convert to UTC then drop tzinfo
                        timestamp = timestamp.astimezone(pytz.UTC).replace(tzinfo=None)
                except Exception:
                    # As a safe fallback use current UTC naive
                    timestamp = datetime.utcnow()
                
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
        df = df.repartition(1, "session_id")  # Use a single partition to minimize Python workers on Windows
        df.cache()  # Cache for multiple operations
        
        # Create a view for SQL queries
        df.createOrReplaceTempView("events")
        
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
                        PERCENTILE(CAST(session_duration_seconds AS DOUBLE), 0.5) as median_session_duration_seconds
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
                    "median_session_duration_seconds": round(session_stats["median_session_duration_seconds"], 2)
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
