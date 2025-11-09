"""
Analytics Orchestrator
Unified interface for managing and coordinating all analytics modules.
Supports both batch and streaming analytics with optimized execution.
"""

import json
import logging
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import analytics modules
from app.spark.ml import (
    ml_kmeans_clustering,
    ml_decision_tree,
    ml_pattern_mining_fpgrowth
)
from app.spark.journey_analytics import analyze_customer_journeys
from app.spark.cart_analytics import analyze_cart_abandonment
from app.spark.retention_analytics import analyze_retention
from app.spark.seo_analytics import analyze_seo_performance
from app.spark.recommendation_als import get_recommendations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def timer_decorator(func: Callable) -> Callable:
    """Decorator to measure execution time of analytics functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            return {
                "data": result,
                "execution_time": execution_time,
                "status": "success"
            }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return {
                "error": str(e),
                "execution_time": execution_time,
                "status": "error"
            }
    return wrapper

class AnalyticsModule:
    """Base class for analytics modules"""
    def __init__(self, name: str, func: Callable, parallel: bool = True):
        self.name = name
        self.func = timer_decorator(func)
        self.parallel = parallel
        self.last_result = None
        
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute the analytics module"""
        self.last_result = self.func(*args, **kwargs)
        return self.last_result

class AnalyticsOrchestrator:
    """
    Orchestrates and manages all analytics operations.
    
    This class coordinates the execution of various analytics modules,
    handling both sequential and parallel processing where appropriate.
    It manages error handling, logging, and result aggregation.
    
    Attributes:
        modules (Dict[str, AnalyticsModule]): Registered analytics modules
        results (Dict[str, Any]): Results from module executions
        errors (Dict[str, str]): Any errors encountered during execution
        start_time (datetime): Execution start timestamp
        end_time (datetime): Execution end timestamp
    """
    
    def __init__(self):
        self.modules: Dict[str, AnalyticsModule] = {
            # ML Modules
            "clustering": AnalyticsModule("Customer Clustering", ml_kmeans_clustering),
            "decision_tree": AnalyticsModule("Purchase Prediction", ml_decision_tree),
            "pattern_mining": AnalyticsModule("Pattern Mining", ml_pattern_mining_fpgrowth),
            
            # Business Analytics
            "customer_journeys": AnalyticsModule("Customer Journeys", analyze_customer_journeys),
            "cart_abandonment": AnalyticsModule("Cart Abandonment", analyze_cart_abandonment),
            "retention": AnalyticsModule("Customer Retention", analyze_retention),
            "seo": AnalyticsModule("SEO Performance", analyze_seo_performance, parallel=False),
            "recommendations": AnalyticsModule("Product Recommendations", get_recommendations)
        }
        
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    def run_all(self, username: Optional[str] = None, limit: Optional[int] = None, 
                max_workers: int = 4) -> Dict[str, Any]:
        """
        Run all analytics modules with optional filtering and parallel execution
        
        Args:
            username: Optional username to analyze specific user
            limit: Optional limit on number of events to process
            max_workers: Maximum number of parallel workers (default: 4)
            
        Returns:
            Dict containing results and execution stats
        """
        self.start_time = datetime.now()
        print(f"🚀 Starting Comprehensive Analytics")
        print(f"   User: {username or 'ALL USERS'}")
        print(f"   Limit: {limit or 'No limit'}")
        print(f"   Max Workers: {max_workers}")
        print(f"{'='*60}\n")

        # Group modules by parallel execution capability
        parallel_modules = []
        sequential_modules = []
        
        modules = [
            ("SEO & Traffic Analysis", self._run_seo_analysis),
            ("Cart Abandonment Analysis", self._run_cart_analysis),
            ("Cohort & Retention Analysis", self._run_retention_analysis),
            ("Customer Journey Analysis", self._run_journey_analysis),
            ("Product Recommendations", self._run_recommendations),
            ("User Segmentation", self._run_segmentation),
            ("Conversion Prediction", self._run_conversion_prediction),
            ("Pattern Mining", self._run_pattern_mining)
        ]
        
        for module_name, module_func in modules:
            if module_name in ["SEO & Traffic Analysis", "Pattern Mining"]:
                sequential_modules.append((module_name, module_func))
            else:
                parallel_modules.append((module_name, module_func))

        # Run sequential modules first
        # Run sequential modules first
        for module_name, module_func in sequential_modules:
            self._run_module(module_name, module_func, username, limit)
            
        # Run parallel modules
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_module = {
                executor.submit(self._run_module, name, func, username, limit): name
                for name, func in parallel_modules
            }
            
            for future in as_completed(future_to_module):
                module_name = future_to_module[future]
                try:
                    future.result()
                except Exception as e:
                    self.errors[module_name] = str(e)
                    logger.error(f"Error in {module_name}: {str(e)}")
                    traceback.print_exc()
        
        # Complete execution and generate report
        # Generate final report
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        # Calculate statistics
        module_stats = {
            "total": len(parallel_modules) + len(sequential_modules),
            "successful": len(self.results) - len(self.errors),
            "failed": len(self.errors),
            "parallel": len(parallel_modules),
            "sequential": len(sequential_modules)
        }
        
        # Print execution summary
        print(f"\n{'='*60}")
        print(f"✅ Analytics Complete")
        print(f"   Duration: {duration:.2f} seconds")
        print(f"   Successful modules: {module_stats['successful']}/{module_stats['total']}")
        
        if self.errors:
            print(f"   Failed modules: {module_stats['failed']}")
            for module, error in self.errors.items():
                print(f"      - {module}: {error}")
        print(f"{'='*60}\n")
        
        # Return comprehensive report
        return {
            "status": "completed",
            "username": username,
            "limit": limit,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": duration,
            "module_statistics": {
                "total": module_stats["total"],
                "successful": module_stats["successful"],
                "failed": module_stats["failed"]
            },
            "parallel_execution": {
                "max_workers": max_workers,
                "parallel_modules": module_stats["parallel"],
                "sequential_modules": module_stats["sequential"]
            },
            "results": self.results,
            "errors": self.errors
        }
        

    def _run_module(self, module_name: str, module_func: Callable, 
                     username: Optional[str], limit: Optional[int]) -> None:
        """
        Execute a single analytics module with error handling
        
        Args:
            module_name: Name of the module to run
            module_func: Function to execute
            username: Optional username filter
            limit: Optional event limit
        """
        print(f"\n📊 Running: {module_name}")
        print(f"   {'-'*50}")
        
        try:
            start_time = time.time()
            result = module_func(username, limit)
            duration = time.time() - start_time
            
            self.results[module_name] = {
                **result,
                "execution_time": duration
            }
            
            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                self.errors[module_name] = result['error']
            else:
                print(f"   ✅ Success ({duration:.2f}s)")
                self._print_module_summary(module_name, result)
                
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Exception: {error_msg}")
            self.errors[module_name] = error_msg
            self.results[module_name] = {
                "error": error_msg,
                "execution_time": time.time() - start_time
            }
            logger.error(f"Error in {module_name}: {error_msg}")
            traceback.print_exc()
    
    def _run_seo_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """Run SEO and traffic analysis"""
        from app.spark.seo_analytics import analyze_seo_performance
        return analyze_seo_performance(username=username, limit=limit)
    
    def _run_cart_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """Run cart abandonment analysis"""
        from app.spark.cart_analytics import analyze_cart_abandonment
        return analyze_cart_abandonment(username=username, limit=limit)
    
    def _run_retention_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """Run cohort and retention analysis"""
        from app.spark.retention_analytics import analyze_retention
        return analyze_retention(username=username, limit=limit)
    
    def _run_journey_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """Run customer journey analysis"""
        from app.spark.journey_analytics import analyze_customer_journeys
        return analyze_customer_journeys(username=username, limit=limit)
    
    def _run_recommendations(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """Run product recommendations"""
        # If username is not provided, run in all-users mode and return sample output
        if not username:
            return self.modules["recommendations"].run(username=None, limit=limit or 10)
        return self.modules["recommendations"].run(username=username, limit=limit)
    
    def _run_segmentation(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """Run customer segmentation"""
        return self.modules["clustering"].run(username=username, limit=limit)
    
    def _run_conversion_prediction(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """Run conversion prediction"""
        return self.modules["decision_tree"].run(username=username, limit=limit)
    
    def _run_pattern_mining(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """Run pattern mining analysis"""
        return self.modules["pattern_mining"].run(username=username, limit=limit)
    
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
