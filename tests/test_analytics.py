"""
test_comprehensive_analytics.py
Test script for all analytics modules
"""

import sys
import traceback
from analytics_orchestrator import AnalyticsOrchestrator


def test_individual_modules():
    """Test each module individually"""
    print("\n" + "="*60)
    print("Testing Individual Analytics Modules")
    print("="*60)
    
    tests = [
        ("SEO Analytics", lambda: test_seo()),
        ("Cart Analytics", lambda: test_cart()),
        ("Retention Analytics", lambda: test_retention()),
        ("Journey Analytics", lambda: test_journey()),
        ("ALS Recommendations", lambda: test_recommendations()),
        ("User Segmentation", lambda: test_segmentation()),
        ("Conversion Prediction", lambda: test_conversion()),
        ("Purchase Probability", lambda: test_purchase()),
        ("Pattern Mining", lambda: test_patterns())
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Testing: {test_name}")
        print(f"{'='*60}")
        try:
            result = test_func()
            if "error" in result:
                print(f"❌ FAILED: {result['error']}")
                results[test_name] = "FAILED"
            else:
                print(f"✅ PASSED")
                results[test_name] = "PASSED"
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            traceback.print_exc()
            results[test_name] = "EXCEPTION"
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    passed = sum(1 for v in results.values() if v == "PASSED")
    failed = sum(1 for v in results.values() if v == "FAILED")
    exceptions = sum(1 for v in results.values() if v == "EXCEPTION")
    
    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Exceptions: {exceptions}")
    
    for test_name, status in results.items():
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {test_name}: {status}")
    
    return results


def test_seo():
    """Test SEO & Traffic Source Analysis"""
    from app.spark.seo_analytics import analyze_traffic_sources
    result = analyze_traffic_sources()
    print(f"Traffic sources found: {len(result.get('traffic_by_source', []))}")
    print(f"Landing pages found: {len(result.get('landing_pages', []))}")
    return result


def test_cart():
    """Test Cart Abandonment Analysis"""
    from app.spark.cart_analytics import analyze_cart_abandonment
    result = analyze_cart_abandonment()
    if "error" not in result:
        print(f"Total carts: {result.get('total_carts', 0)}")
        print(f"Abandonment rate: {result.get('abandonment_rate', 0)}%")
    return result


def test_retention():
    """Test Cohort & Retention Analysis"""
    from app.spark.retention_analytics import analyze_cohort_retention
    result = analyze_cohort_retention()
    if "error" not in result:
        print(f"Cohorts analyzed: {len(result.get('cohorts', []))}")
        avg_ret = result.get('average_retention', {})
        print(f"Avg Week 1 retention: {avg_ret.get('week1', 0)}%")
    return result


def test_journey():
    """Test Customer Journey Analysis"""
    from app.spark.journey_analytics import analyze_customer_journey
    result = analyze_customer_journey()
    if "error" not in result:
        print(f"Conversion paths: {len(result.get('conversion_paths', []))}")
        print(f"Drop-off points: {len(result.get('dropoff_points', []))}")
    return result


def test_recommendations():
    """Test ALS Recommendations"""
    from app.spark.recommendation_als import ml_product_recommendations_als
    # Get a user first
    from app.core.db_sync import users_col
    user = users_col().find_one({})
    if not user:
        return {"error": "No users found"}
    
    username = user.get("username")
    result = ml_product_recommendations_als(username=username, top_n=5)
    if "error" not in result:
        recs = result.get('recommendations', [])
        print(f"Recommendations for {username}: {len(recs)}")
    return result


def test_segmentation():
    """Test User Segmentation"""
    from app.spark.ml import ml_user_segmentation_kmeans
    result = ml_user_segmentation_kmeans()
    if "error" not in result:
        print(f"Clusters: {result.get('num_clusters', 0)}")
        print(f"Silhouette score: {result.get('silhouette_score', 0)}")
    return result


def test_conversion():
    """Test Conversion Prediction"""
    from app.spark.ml import ml_conversion_prediction_tree
    result = ml_conversion_prediction_tree()
    if "error" not in result:
        print(f"AUC: {result.get('auc_score', 0)}")
        print(f"Tree depth: {result.get('tree_depth', 0)}")
    return result


def test_purchase():
    """Test Purchase Probability"""
    from app.spark.ml import ml_purchase_prediction_logistic
    result = ml_purchase_prediction_logistic()
    if "error" not in result:
        print(f"AUC: {result.get('auc_score', 0)}")
        print(f"Training samples: {result.get('training_samples', 0)}")
    return result


def test_patterns():
    """Test Pattern Mining"""
    from app.spark.ml import ml_pattern_mining_fpgrowth
    result = ml_pattern_mining_fpgrowth()
    if "error" not in result:
        print(f"Patterns: {len(result.get('top_patterns', []))}")
        print(f"Rules: {len(result.get('top_rules', []))}")
    return result


def test_orchestrator():
    """Test the unified orchestrator"""
    print("\n" + "="*60)
    print("Testing Analytics Orchestrator")
    print("="*60)
    
    orchestrator = AnalyticsOrchestrator()
    results = orchestrator.run_all()
    
    # Export results
    orchestrator.export_to_json("test_analytics_results.json")
    
    return results


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test analytics modules")
    parser.add_argument("--mode", choices=["individual", "orchestrator", "all"], 
                       default="all", help="Test mode")
    
    args = parser.parse_args()
    
    if args.mode in ["individual", "all"]:
        test_individual_modules()
    
    if args.mode in ["orchestrator", "all"]:
        test_orchestrator()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    main()
