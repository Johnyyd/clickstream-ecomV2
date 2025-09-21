# test_full_flow.py - Test the complete flow
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_full_flow():
    print("=== Testing Complete Clickstream Flow ===")
    
    # 1. Create a test user
    print("\n1. Creating test user...")
    signup_data = {
        "username": "alice",
        "email": "alice@example.com", 
        "password": "alice123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/signup", json=signup_data)
        print(f"Signup status: {response.status_code}")
        if response.status_code == 201:
            print("User created successfully")
        else:
            print(f"Signup response: {response.text}")
    except Exception as e:
        print(f"Signup error: {e}")
    
    # 2. Login
    print("\n2. Logging in...")
    login_data = {
        "username": "alice",
        "password": "alice123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/login", json=login_data)
        print(f"Login status: {response.status_code}")
        if response.status_code == 200:
            token = response.json().get("token")
            print(f"Login successful, token: {token[:20]}...")
        else:
            print(f"Login response: {response.text}")
            return
    except Exception as e:
        print(f"Login error: {e}")
        return
    
    # 3. Simulate some events
    print("\n3. Simulating events...")
    events = [
        {"client_id": "test-client", "page": "/home", "event_type": "pageview", "session_id": "session-1"},
        {"client_id": "test-client", "page": "/product", "event_type": "pageview", "session_id": "session-1"},
        {"client_id": "test-client", "page": "/checkout", "event_type": "pageview", "session_id": "session-1"},
        {"client_id": "test-client", "page": "/home", "event_type": "pageview", "session_id": "session-2"},
        {"client_id": "test-client", "page": "/product", "event_type": "pageview", "session_id": "session-2"},
    ]
    
    for i, event in enumerate(events):
        try:
            response = requests.post(f"{BASE_URL}/api/ingest", 
                                   headers={"Authorization": token}, 
                                   json=event)
            if response.status_code == 201:
                print(f"Event {i+1} ingested successfully")
            else:
                print(f"Event {i+1} failed: {response.text}")
        except Exception as e:
            print(f"Event {i+1} error: {e}")
    
    # 4. Run analysis
    print("\n4. Running analysis...")
    try:
        response = requests.post(f"{BASE_URL}/api/analyze", 
                               headers={"Authorization": token, "Content-Type": "application/json"}, 
                               json={"params": {"limit": 100}})
        print(f"Analysis status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Analysis result: {result}")
            
            # Get detailed analysis
            if "analysis" in result and "_id" in result["analysis"]:
                analysis_id = result["analysis"]["_id"]
                print(f"\n5. Getting detailed analysis for ID: {analysis_id}")
                
                detail_response = requests.get(f"{BASE_URL}/api/analyses/{analysis_id}", 
                                             headers={"Authorization": token})
                if detail_response.status_code == 200:
                    analysis_detail = detail_response.json()
                    print("Detailed analysis:")
                    print(f"- Total Events: {analysis_detail.get('spark_summary', {}).get('total_events', 0)}")
                    print(f"- Total Sessions: {analysis_detail.get('spark_summary', {}).get('sessions', 0)}")
                    print(f"- Top Pages: {analysis_detail.get('spark_summary', {}).get('top_pages', [])}")
                    print(f"- Home to Product Conversion: {analysis_detail.get('spark_summary', {}).get('funnel_home_to_product', 0)}")
                else:
                    print(f"Failed to get analysis detail: {detail_response.text}")
        else:
            print(f"Analysis failed: {response.text}")
    except Exception as e:
        print(f"Analysis error: {e}")

if __name__ == "__main__":
    test_full_flow()
