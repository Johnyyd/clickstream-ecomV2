"""
Test configuration for Spark jobs
"""
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    """Create Spark session for testing"""
    spark = (SparkSession.builder
        .master("local[2]")
        .appName("clickstream-test")
        .config("spark.driver.host", "localhost")
        .config("spark.executor.memory", "2g")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.default.parallelism", "2")
        .getOrCreate())
    
    yield spark
    
    spark.stop()

@pytest.fixture
def sample_events(spark):
    """Create sample events DataFrame"""
    data = [
        ("s1", "page_view", "home", "2024-01-01"),
        ("s1", "add_to_cart", "product1", "2024-01-01"),
        ("s2", "page_view", "product2", "2024-01-01"),
        ("s2", "checkout", None, "2024-01-01")
    ]
    
    return spark.createDataFrame(
        data,
        ["session_id", "event_type", "page", "date"]
    )

@pytest.fixture
def sample_products(spark):
    """Create sample products DataFrame"""
    data = [
        (1, "Product 1", "Category A", 10.0),
        (2, "Product 2", "Category B", 20.0)
    ]
    
    return spark.createDataFrame(
        data,
        ["id", "name", "category", "price"]
    )