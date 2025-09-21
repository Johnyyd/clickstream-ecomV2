# test_new_analysis_api.py - Test the new detailed analysis API
import requests
import json

BASE_URL = "http://localhost:8000"

def test_new_analysis_api():
    print("=== Testing New Detailed Analysis API ===")
    
    # 1. Login to get token
    print("\n1. Logging in...")
    login_data = {
        "username": "alice",
        "password": "alice123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"Login successful, token: {token[:20]}...")
        else:
            print(f"Login failed: {response.text}")
            return
    except Exception as e:
        print(f"Login error: {e}")
        return
    
    # 2. Run analysis
    print("\n2. Running detailed analysis...")
    try:
        response = requests.post(f"{BASE_URL}/api/analyze", 
                               headers={"Authorization": token, "Content-Type": "application/json"}, 
                               json={"params": {"limit": 1000}})
        print(f"Analysis status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Analysis result: {result}")
            
            # Get detailed analysis
            if "analysis" in result and "_id" in result["analysis"]:
                analysis_id = result["analysis"]["_id"]
                print(f"\n3. Getting detailed analysis for ID: {analysis_id}")
                
                detail_response = requests.get(f"{BASE_URL}/api/analyses/{analysis_id}", 
                                             headers={"Authorization": token})
                if detail_response.status_code == 200:
                    analysis_detail = detail_response.json()
                    
                    # Display comprehensive results
                    print("\n=== COMPREHENSIVE ANALYSIS RESULTS ===")
                    
                    # Basic summary
                    spark_summary = analysis_detail.get('spark_summary', {})
                    print(f"\n📊 Basic Summary:")
                    print(f"  - Total Events: {spark_summary.get('total_events', 0)}")
                    print(f"  - Total Sessions: {spark_summary.get('sessions', 0)}")
                    print(f"  - Top Pages: {spark_summary.get('top_pages', [])[:5]}")
                    
                    # Detailed metrics
                    detailed_metrics = analysis_detail.get('detailed_metrics', {})
                    if detailed_metrics:
                        basic_metrics = detailed_metrics.get('basic_metrics', {})
                        print(f"\n📈 Detailed Metrics:")
                        print(f"  - Unique Users: {basic_metrics.get('unique_users', 0)}")
                        print(f"  - Bounce Rate: {basic_metrics.get('bounce_rate', 0):.2%}")
                        print(f"  - Avg Session Duration: {basic_metrics.get('avg_session_duration_seconds', 0):.1f} seconds")
                        print(f"  - Avg Pages per Session: {basic_metrics.get('avg_pages_per_session', 0):.1f}")
                        
                        # Funnel analysis
                        funnel_analysis = detailed_metrics.get('funnel_analysis', {})
                        print(f"\n🔄 Funnel Analysis:")
                        for funnel_name, funnel_data in funnel_analysis.items():
                            if funnel_data.get('conversion', 0) > 0:
                                print(f"  - {funnel_name}: {funnel_data['conversion']:.2%} conversion rate")
                        
                        # Time analysis
                        time_analysis = detailed_metrics.get('time_analysis', {})
                        print(f"\n⏰ Time Analysis:")
                        print(f"  - Peak Hour: {time_analysis.get('peak_hour', 'N/A')}:00")
                        print(f"  - Peak Day: {time_analysis.get('peak_day', 'N/A')}")
                        
                        # User analysis
                        user_analysis = detailed_metrics.get('user_analysis', {})
                        print(f"\n👥 User Analysis:")
                        print(f"  - Avg Sessions per User: {user_analysis.get('avg_sessions_per_user', 0):.1f}")
                        print(f"  - Avg Events per User: {user_analysis.get('avg_events_per_user', 0):.1f}")
                    
                    # Insights
                    insights = analysis_detail.get('insights', {})
                    if insights:
                        print(f"\n💡 Generated Insights:")
                        
                        key_findings = insights.get('key_findings', [])
                        if key_findings:
                            print("  Key Findings:")
                            for finding in key_findings:
                                print(f"    - {finding}")
                        
                        recommendations = insights.get('recommendations', [])
                        if recommendations:
                            print("  Recommendations:")
                            for rec in recommendations:
                                print(f"    - {rec}")
                        
                        alerts = insights.get('alerts', [])
                        if alerts:
                            print("  Alerts:")
                            for alert in alerts:
                                print(f"    - ⚠️ {alert}")
                    
                    # Analysis metadata
                    metadata = analysis_detail.get('analysis_metadata', {})
                    if metadata:
                        print(f"\n📋 Analysis Metadata:")
                        print(f"  - Version: {metadata.get('analysis_version', 'N/A')}")
                        print(f"  - Type: {metadata.get('analysis_type', 'N/A')}")
                        print(f"  - Data Quality: {metadata.get('data_quality', {})}")
                    
                    print(f"\n✅ SUCCESS: Comprehensive analysis completed!")
                    print(f"This detailed data is now saved in MongoDB for future analysis.")
                    
                else:
                    print(f"Failed to get analysis detail: {detail_response.text}")
        else:
            print(f"Analysis failed: {response.text}")
    except Exception as e:
        print(f"Analysis error: {e}")

if __name__ == "__main__":
    test_new_analysis_api()
