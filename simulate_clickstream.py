# simulate_clickstream.py
from ingest import ingest_event
import random, time
from datetime import datetime, timedelta

pages = ["/home","/product","/category","/checkout","/search"]
session_duration = 1800  # 30 minutes in seconds

def create_session():
    return {
        "session_id": f"session_{random.randint(1,1000)}",
        "client_id": f"client_{random.randint(1,50)}",
        "start_time": int(time.time()) - random.randint(0, 86400)  # Within last 24 hours
    }

def simulate_session(session, num_events=5):
    current_time = session["start_time"]
    # Start with home page
    events = [{
        "session_id": session["session_id"],
        "client_id": session["client_id"],
        "page": "/home",
        "event_type": "pageview",
        "timestamp": current_time
    }]
    
    # Add more events with higher probability of product views after home
    for i in range(num_events - 1):
        current_time += random.randint(10, 300)  # 10s to 5min between events
        if i == 1:  # Second event has higher chance to be product
            page = "/product" if random.random() < 0.7 else random.choice(pages)
        else:
            page = random.choice(pages)
        
        events.append({
            "session_id": session["session_id"],
            "client_id": session["client_id"],
            "page": page,
            "event_type": "pageview",
            "timestamp": current_time
        })
    return events

def simulate(num_sessions=20):
    total_events = 0
    for _ in range(num_sessions):
        session = create_session()
        events = simulate_session(session, random.randint(3, 8))
        for ev in events:
            ingest_event(ev)
            total_events += 1
    return total_events

if __name__ == "__main__":
    total = simulate(20)
    print(f"Inserted {total} events across 20 sessions")
