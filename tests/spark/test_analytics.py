"""
Tests for Spark analytics jobs
"""
import pytest
from pyspark.sql import functions as F

from spark_journey_analytics import analyze_user_journeys
from spark_cart_analytics import analyze_cart_behavior
from spark_retention_analytics import analyze_user_retention

def test_journey_analysis(spark, sample_events):
    """Test journey analysis job"""
    result = analyze_user_journeys(sample_events)
    
    # Check output structure
    assert "paths" in result
    assert "conversions" in result
    
    # Validate path analysis
    paths = result["paths"]
    assert len(paths) > 0
    assert all("path" in p and "count" in p for p in paths)
    
    # Check conversion analysis
    conversions = result["conversions"]
    assert isinstance(conversions, dict)
    assert "checkout_rate" in conversions

def test_cart_analysis(spark, sample_events):
    """Test cart analysis job"""
    result = analyze_cart_behavior(sample_events)
    
    # Check metrics
    assert "abandonment_rate" in result
    assert isinstance(result["abandonment_rate"], float)
    
    # Check product combinations
    assert "product_combinations" in result
    combinations = result["product_combinations"]
    assert len(combinations) > 0
    assert all("products" in c and "frequency" in c for c in combinations)

def test_retention_analysis(spark, sample_events):
    """Test retention analysis job"""
    result = analyze_user_retention(sample_events)
    
    # Check cohort matrix
    assert "cohort_matrix" in result
    matrix = result["cohort_matrix"]
    assert len(matrix) > 0
    
    # Check retention metrics
    assert "retention_rates" in result
    rates = result["retention_rates"]
    assert isinstance(rates, dict)
    assert all(isinstance(v, float) for v in rates.values())