# view_analysis_data.py - View detailed analysis data from MongoDB
from app.core.db_sync import analyses_col
from bson import ObjectId
import json
from datetime import datetime

def view_analysis_data():
    print("=== Viewing Analysis Data from MongoDB ===")
    
    # Get the latest analysis
    latest_analysis = analyses_col().find_one(
        {"analysis_metadata.analysis_version": "2.0"},
        sort=[("created_at", -1)]
    )
    
    if not latest_analysis:
        print("No detailed analysis found in MongoDB")
        return
    
    print(f"Latest Analysis ID: {latest_analysis['_id']}")
    print(f"Created: {latest_analysis['created_at']}")
    print(f"User ID: {latest_analysis['user_id']}")
    
    # Display basic summary
    spark_summary = latest_analysis.get('spark_summary', {})
    print(f"\n=== Basic Summary ===")
    print(f"Total Events: {spark_summary.get('total_events', 0)}")
    print(f"Total Sessions: {spark_summary.get('sessions', 0)}")
    print(f"Top Pages: {spark_summary.get('top_pages', [])[:5]}")
    
    # Display detailed metrics
    detailed_metrics = latest_analysis.get('detailed_metrics', {})
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
        
        # Page analysis
        page_analysis = detailed_metrics.get('page_analysis', {})
        print(f"\n=== Page Analysis ===")
        top_pages = page_analysis.get('top_pages', [])
        print("Top 10 Pages:")
        for i, page in enumerate(top_pages[:10], 1):
            print(f"  {i}. {page['page']}: {page['count']} visits")
        
        # Event analysis
        event_analysis = detailed_metrics.get('event_analysis', {})
        print(f"\n=== Event Analysis ===")
        event_types = event_analysis.get('event_types', {})
        print("Event Types:")
        for event_type, count in event_types.items():
            print(f"  - {event_type}: {count}")
        
        # Conversion rates
        conversion_rates = detailed_metrics.get('conversion_rates', {})
        print(f"\n=== Conversion Rates ===")
        page_visit_rates = conversion_rates.get('page_visit_rates', {})
        print("Page Visit Rates:")
        for page, rate in list(page_visit_rates.items())[:10]:
            print(f"  - {page}: {rate:.2%}")
        
        print(f"Multi-page Session Rate: {conversion_rates.get('multi_page_session_rate', 0):.2%}")
        print(f"Return Visitor Rate: {conversion_rates.get('return_visitor_rate', 0):.2%}")
    
    # Display insights
    insights = latest_analysis.get('insights', {})
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
    metadata = latest_analysis.get('analysis_metadata', {})
    if metadata:
        print(f"\n=== Analysis Metadata ===")
        print(f"Analysis Version: {metadata.get('analysis_version', 'N/A')}")
        print(f"Analysis Type: {metadata.get('analysis_type', 'N/A')}")
        
        data_quality = metadata.get('data_quality', {})
        print(f"Data Quality: {data_quality}")
    
    print(f"\n✅ Analysis data successfully retrieved from MongoDB!")
    print(f"This comprehensive data can be used for deeper analysis and reporting.")

if __name__ == "__main__":
    view_analysis_data()
