# test_detailed_analysis.py - Test the new detailed analysis
from analysis import run_analysis
from bson import ObjectId
import json

def test_detailed_analysis():
    print("=== Testing Detailed Analysis ===")
    
    # Test with a known user ID
    user_id = "68cf83c71e293f2fd9767a59"  # From previous successful test
    
    print(f"Running detailed analysis for user: {user_id}")
    result = run_analysis(user_id, {"limit": 1000})
    
    print(f"\nAnalysis result ID: {result.get('_id')}")
    
    # Display basic summary
    spark_summary = result.get('spark_summary', {})
    print(f"\n=== Basic Summary ===")
    print(f"Total Events: {spark_summary.get('total_events', 0)}")
    print(f"Total Sessions: {spark_summary.get('sessions', 0)}")
    print(f"Top Pages: {spark_summary.get('top_pages', [])[:5]}")
    
    # Display detailed metrics
    detailed_metrics = result.get('detailed_metrics', {})
    if detailed_metrics:
        print(f"\n=== Detailed Metrics ===")
        
        # Basic metrics
        basic_metrics = detailed_metrics.get('basic_metrics', {})
        print(f"Unique Users: {basic_metrics.get('unique_users', 0)}")
        print(f"Bounce Rate: {basic_metrics.get('bounce_rate', 0):.2%}")
        print(f"Avg Session Duration: {basic_metrics.get('avg_session_duration_seconds', 0):.1f} seconds")
        print(f"Avg Pages per Session: {basic_metrics.get('avg_pages_per_session', 0):.1f}")
        
        # Funnel analysis
        funnel_analysis = detailed_metrics.get('funnel_analysis', {})
        print(f"\n=== Funnel Analysis ===")
        for funnel_name, funnel_data in funnel_analysis.items():
            if funnel_data.get('conversion', 0) > 0:
                print(f"{funnel_name}: {funnel_data['conversion']:.2%} conversion rate")
        
        # Time analysis
        time_analysis = detailed_metrics.get('time_analysis', {})
        print(f"\n=== Time Analysis ===")
        print(f"Peak Hour: {time_analysis.get('peak_hour', 'N/A')}:00")
        print(f"Peak Day: {time_analysis.get('peak_day', 'N/A')}")
        
        # User analysis
        user_analysis = detailed_metrics.get('user_analysis', {})
        print(f"\n=== User Analysis ===")
        print(f"Avg Sessions per User: {user_analysis.get('avg_sessions_per_user', 0):.1f}")
        print(f"Avg Events per User: {user_analysis.get('avg_events_per_user', 0):.1f}")
    
    # Display insights
    insights = result.get('insights', {})
    if insights:
        print(f"\n=== Generated Insights ===")
        
        key_findings = insights.get('key_findings', [])
        if key_findings:
            print("Key Findings:")
            for finding in key_findings:
                print(f"  - {finding}")
        
        recommendations = insights.get('recommendations', [])
        if recommendations:
            print("\nRecommendations:")
            for rec in recommendations:
                print(f"  - {rec}")
        
        alerts = insights.get('alerts', [])
        if alerts:
            print("\nAlerts:")
            for alert in alerts:
                print(f"  - ⚠️ {alert}")
    
    # Display analysis metadata
    metadata = result.get('analysis_metadata', {})
    if metadata:
        print(f"\n=== Analysis Metadata ===")
        print(f"Analysis Version: {metadata.get('analysis_version', 'N/A')}")
        print(f"Analysis Type: {metadata.get('analysis_type', 'N/A')}")
        
        data_quality = metadata.get('data_quality', {})
        print(f"Data Quality: {data_quality}")
    
    print(f"\n✅ Detailed analysis completed successfully!")
    print(f"Analysis saved to MongoDB with comprehensive metrics for future analysis.")

if __name__ == "__main__":
    test_detailed_analysis()
