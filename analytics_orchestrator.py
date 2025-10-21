"""
analytics_orchestrator.py - Unified Analytics Orchestrator
Quản lý và điều phối tất cả các module phân tích
"""

import traceback
from datetime import datetime
from typing import Dict, List, Optional
import json


class AnalyticsOrchestrator:
    """
    Orchestrator for all analytics modules
    Provides a unified interface to run all analyses
    """
    
    def __init__(self):
        self.results = {}
        self.errors = {}
        self.start_time = None
        self.end_time = None
    
    def run_all(self, username: Optional[str] = None, limit: Optional[int] = None) -> Dict:
        """
        Run all analytics modules
        Returns comprehensive results
        """
        self.start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"🚀 Starting Comprehensive Analytics")
        print(f"   User: {username or 'ALL USERS'}")
        print(f"   Limit: {limit or 'No limit'}")
        print(f"{'='*60}\n")
        
        modules = [
            ("SEO & Traffic Analysis", self._run_seo_analysis),
            ("Cart Abandonment Analysis", self._run_cart_analysis),
            ("Cohort & Retention Analysis", self._run_retention_analysis),
            ("Customer Journey Analysis", self._run_journey_analysis),
            ("Product Recommendations (ALS)", self._run_recommendations),
            ("User Segmentation (K-Means)", self._run_segmentation),
            ("Conversion Prediction (Decision Tree)", self._run_conversion_prediction),
            ("Purchase Probability (Logistic Regression)", self._run_purchase_prediction),
            ("Pattern Mining (FP-Growth)", self._run_pattern_mining)
        ]
        
        for module_name, module_func in modules:
            print(f"\n📊 Running: {module_name}")
            print(f"   {'-'*50}")
            try:
                result = module_func(username, limit)
                self.results[module_name] = result
                
                # Print summary
                if "error" in result:
                    print(f"   ❌ Error: {result['error']}")
                    self.errors[module_name] = result['error']
                else:
                    print(f"   ✅ Success")
                    self._print_module_summary(module_name, result)
                    
            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ Exception: {error_msg}")
                self.errors[module_name] = error_msg
                self.results[module_name] = {"error": error_msg}
                traceback.print_exc()
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"✅ Analytics Complete")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Successful modules: {len(self.results) - len(self.errors)}/{len(self.results)}")
        if self.errors:
            print(f"   Failed modules: {len(self.errors)}")
            for module, error in self.errors.items():
                print(f"      - {module}: {error}")
        print(f"{'='*60}\n")
        
        return {
            "status": "completed",
            "username": username,
            "limit": limit,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": duration,
            "total_modules": len(modules),
            "successful_modules": len(self.results) - len(self.errors),
            "failed_modules": len(self.errors),
            "results": self.results,
            "errors": self.errors
        }
    
    def _run_seo_analysis(self, username, limit):
        from spark_seo_analytics import analyze_traffic_sources
        return analyze_traffic_sources(username=username)
    
    def _run_cart_analysis(self, username, limit):
        from spark_cart_analytics import analyze_cart_abandonment
        return analyze_cart_abandonment(username=username)
    
    def _run_retention_analysis(self, username, limit):
        from spark_retention_analytics import analyze_cohort_retention
        return analyze_cohort_retention(username=username)
    
    def _run_journey_analysis(self, username, limit):
        from spark_journey_analytics import analyze_customer_journey
        return analyze_customer_journey(username=username)
    
    def _run_recommendations(self, username, limit):
        if not username:
            return {"error": "Username required for recommendations"}
        from spark_recommendation_als import ml_product_recommendations_als
        return ml_product_recommendations_als(username=username, top_n=5)
    
    def _run_segmentation(self, username, limit):
        from spark_ml import ml_user_segmentation_kmeans
        return ml_user_segmentation_kmeans(username=username)
    
    def _run_conversion_prediction(self, username, limit):
        from spark_ml import ml_conversion_prediction_tree
        return ml_conversion_prediction_tree(username=username)
    
    def _run_purchase_prediction(self, username, limit):
        from spark_ml import ml_purchase_prediction_logistic
        return ml_purchase_prediction_logistic(username=username)
    
    def _run_pattern_mining(self, username, limit):
        from spark_ml import ml_pattern_mining_fpgrowth
        return ml_pattern_mining_fpgrowth(username=username)
    
    def _print_module_summary(self, module_name: str, result: Dict):
        """Print a concise summary of module results"""
        try:
            if module_name == "SEO & Traffic Analysis":
                sources = result.get("traffic_by_source", [])
                print(f"      Sources: {len(sources)}")
                if sources:
                    top_source = sources[0]
                    print(f"      Top source: {top_source['source']} ({top_source['sessions']} sessions)")
            
            elif module_name == "Cart Abandonment Analysis":
                rate = result.get("abandonment_rate", 0)
                total = result.get("total_carts", 0)
                print(f"      Abandonment rate: {rate}%")
                print(f"      Total carts: {total}")
            
            elif module_name == "Cohort & Retention Analysis":
                cohorts = result.get("cohorts", [])
                avg_ret = result.get("average_retention", {})
                print(f"      Cohorts analyzed: {len(cohorts)}")
                print(f"      Avg Week 1 retention: {avg_ret.get('week1', 0)}%")
            
            elif module_name == "Customer Journey Analysis":
                paths = result.get("conversion_paths", [])
                dropoffs = result.get("dropoff_points", [])
                print(f"      Conversion paths: {len(paths)}")
                print(f"      Drop-off points: {len(dropoffs)}")
            
            elif module_name == "Product Recommendations (ALS)":
                recs = result.get("recommendations", [])
                rmse = result.get("rmse", 0)
                print(f"      Recommendations: {len(recs)}")
                print(f"      RMSE: {rmse}")
            
            elif module_name == "User Segmentation (K-Means)":
                clusters = result.get("cluster_stats", {})
                silhouette = result.get("silhouette_score", 0)
                print(f"      Clusters: {len(clusters)}")
                print(f"      Silhouette score: {silhouette}")
            
            elif module_name == "Conversion Prediction (Decision Tree)":
                auc = result.get("auc_score", 0)
                depth = result.get("tree_depth", 0)
                print(f"      AUC: {auc}")
                print(f"      Tree depth: {depth}")
            
            elif module_name == "Purchase Probability (Logistic Regression)":
                auc = result.get("auc_score", 0)
                samples = result.get("training_samples", 0)
                print(f"      AUC: {auc}")
                print(f"      Training samples: {samples}")
            
            elif module_name == "Pattern Mining (FP-Growth)":
                patterns = result.get("top_patterns", [])
                rules = result.get("top_rules", [])
                print(f"      Patterns found: {len(patterns)}")
                print(f"      Rules found: {len(rules)}")
                
        except Exception as e:
            print(f"      (Summary unavailable: {e})")
    
    def export_to_json(self, filepath: str = "analytics_results.json"):
        """Export results to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "start_time": self.start_time.isoformat() if self.start_time else None,
                    "end_time": self.end_time.isoformat() if self.end_time else None,
                    "results": self.results,
                    "errors": self.errors
                }, f, indent=2, default=str)
            print(f"✅ Results exported to: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False


def main():
    """
    CLI interface for running analytics
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Run comprehensive clickstream analytics")
    parser.add_argument("--username", type=str, help="Analyze specific user")
    parser.add_argument("--limit", type=int, help="Limit number of events")
    parser.add_argument("--export", type=str, default="analytics_results.json", 
                       help="Export results to JSON file")
    
    args = parser.parse_args()
    
    orchestrator = AnalyticsOrchestrator()
    results = orchestrator.run_all(username=args.username, limit=args.limit)
    
    if args.export:
        orchestrator.export_to_json(args.export)
    
    return results


if __name__ == "__main__":
    main()
