import sys
import os
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import random, uuid

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# giả sử bạn đã insert sample_users vào MongoDB
from db import users_col, events_col

def generate_clickstream(users, events_per_user=10):
    pages = ["/home", "/search", "/product/101", "/product/202", "/product/303", "/cart", "/checkout"]
    event_types = ["pageview", "click", "add_to_cart", "checkout"]
    
    all_events = []
    base_time = datetime.now(timezone.utc)
    
    for u in users:
        uid = u["_id"]
        session_id = str(uuid.uuid4())
        t = base_time
        for i in range(events_per_user):
            page = random.choice(pages)
            etype = "pageview"
            if "product" in page and random.random() < 0.3:
                etype = "add_to_cart"
            elif page == "/checkout":
                etype = "checkout"
            elif random.random() < 0.2:
                etype = "click"
            
            ev = {
                "_id": ObjectId(),
                "user_id": uid,
                "client_id": f"client_{uid}",
                "timestamp": t,
                "page": page,
                "event_type": etype,
                "properties": {"browser": random.choice(["Chrome","Firefox","Edge"])},
                "session_id": session_id
            }
            all_events.append(ev)
            # tăng thời gian 30–120 giây mỗi event
            t += timedelta(seconds=random.randint(30,120))
    
    return all_events

if __name__ == "__main__":
    users = list(users_col().find().limit(10))  # lấy 10 user mẫu
    events = generate_clickstream(users, events_per_user=10)
    events_col().insert_many(events)
    print(f"Inserted {len(events)} events for {len(users)} users")
