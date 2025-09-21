# test_analysis_api.py - Test analysis API with proper authentication
import requests
import json

BASE_URL = "http://localhost:8000"

def test_analysis_api():
    print("=== Testing Analysis API ===")
    
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
    print("\n2. Running analysis...")
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
                    print("Detailed analysis:")
                    spark_summary = analysis_detail.get('spark_summary', {})
                    print(f"- Total Events: {spark_summary.get('total_events', 0)}")
                    print(f"- Total Sessions: {spark_summary.get('sessions', 0)}")
                    print(f"- Top Pages: {spark_summary.get('top_pages', [])[:5]}")
                    print(f"- Home to Product Conversion: {spark_summary.get('funnel_home_to_product', 0)}")
                    
                    # Check if we have real data
                    if spark_summary.get('total_events', 0) > 0:
                        print("\n✅ SUCCESS: Analysis is working with real data!")
                    else:
                        print("\n❌ ISSUE: Analysis returned 0 events")
                else:
                    print(f"Failed to get analysis detail: {detail_response.text}")
        else:
            print(f"Analysis failed: {response.text}")
    except Exception as e:
        print(f"Analysis error: {e}")

if __name__ == "__main__":
    test_analysis_api()
