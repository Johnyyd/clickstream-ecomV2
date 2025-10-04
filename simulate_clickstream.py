# simulate_clickstream.py
from ingest import ingest_event
from db import get_db, users_col, sessions_col, products_col
from bson import ObjectId
import random, time
from datetime import datetime, timedelta

# Enhanced pages with product-specific pages
pages = ["/home", "/category", "/search", "/checkout", "/cart"]
session_duration = 1800  # 30 minutes in seconds

def ensure_products():
    """Ensure there are products in MongoDB; seed via seed_products.py if empty."""
    if products_col().count_documents({}) == 0:
        try:
            from seed_products import seed_more_products
            seed_more_products()
        except Exception as e:
            print(f"Failed to seed products: {e}")
    return list(products_col().find({}))

def get_random_product(products):
    """Get a random product from the products list"""
    return random.choice(products)

def get_products_by_category(category):
    """Get products filtered by category from DB"""
    return list(products_col().find({"category": category}))

def get_or_create_test_users():
    """Get existing users or create test users for simulation"""
    users = list(users_col().find({}))
    
    if not users:
        print("No users found, creating test users...")
        # Create some test users
        test_users = [
            {"username": "customer001", "email": "customer001@example.com", "password": "customer001123"},
            
        ]
        
        for user_data in test_users:
            try:
                from auth import create_user
                user_id = create_user(
                    user_data["username"], 
                    user_data["email"], 
                    user_data["password"]
                )
                print(f"Created user: {user_data['username']} (ID: {user_id})")
            except ValueError as e:
                print(f"User {user_data['username']} already exists: {e}")
        
        # Get users again
        users = list(users_col().find({}))
    
    return users

def create_session_with_real_user():
    """Create a session using real user IDs from database"""
    users = get_or_create_test_users()
    
    if not users:
        # Fallback to string IDs if no users found
        return {
            "session_id": f"session_{random.randint(1,1000)}",
            "client_id": f"client_{random.randint(1,50)}",
            "user_id": f"user_{random.randint(1,20)}",
            "start_time": int(time.time()) - random.randint(0, 86400)
        }
    
    # Select a random user
    user = random.choice(users)
    user_id = user["_id"]  # Keep as ObjectId, not string
    
    # Create a unique session ID using user's ObjectId
    session_id = f"session_{str(user_id)[-6:]}_{random.randint(1000, 9999)}"
    client_id = f"client_{str(user_id)[-6:]}_{random.randint(1, 100)}"
    
    return {
        "session_id": session_id,
        "client_id": client_id,
        "user_id": user_id,  # This will be ObjectId
        "start_time": int(time.time()) - random.randint(0, 86400)
    }

def create_session():
    """Create a session with consistent ID management"""
    return create_session_with_real_user()

def simulate_session(session, num_events=5, products=None):
    if products is None:
        products = list(products_col().find({}))
        if not products:
            print("Warning: No products found in database. Please run seed_products.py first.")
            return []
    
    current_time = session["start_time"]
    events = []
    viewed_products = set()
    cart_items = []
    
    # Start with home page
    events.append({
        "session_id": session["session_id"],
        "client_id": session["client_id"],
        "user_id": session["user_id"],
        "page": "/home",
        "event_type": "pageview",
        "timestamp": current_time,
        "properties": {"referrer": "direct"}
    })
    
    # Simulate realistic user journey
    for i in range(num_events - 1):
        current_time += random.randint(10, 300)  # 10s to 5min between events
        
        # Determine next action based on current state and probabilities
        if i == 1:  # Second event - likely to browse categories or search
            if random.random() < 0.6:
                page = "/category"
                category = random.choice(["computer", "phone", "drink", "food", "glasses", "pants", "shoes", "shirt"])
                event_type = "pageview"
                properties = {"category": category}
            elif random.random() < 0.8:
                page = "/search"
                search_term = random.choice(["laptop", "phone", "coffee", "pizza", "shoes", "shirt"])
                event_type = "search"
                properties = {"search_term": search_term}
            else:
                page = random.choice(pages)
                event_type = "pageview"
                properties = {}
        
        elif len(viewed_products) > 0 and random.random() < 0.3:  # 30% chance to view specific product
            product = get_random_product(products)
            viewed_products.add(str(product["_id"]))
            page = f"/product/{product['_id']}"
            event_type = "pageview"
            properties = {
                "product_id": str(product["_id"]),
                "product_name": product["name"],
                "product_category": product["category"],
                "product_price": product["price"]
            }
        
        elif random.random() < 0.2:  # 20% chance to add to cart
            if viewed_products:
                product_id = random.choice(list(viewed_products))
                product = next((p for p in products if str(p["_id"]) == product_id), None)
                if not product:  # Fallback to random product if not found
                    product = get_random_product(products)
                cart_items.append(product)
                page = "/cart"
                event_type = "add_to_cart"
                properties = {
                    "product_id": str(product["_id"]),
                    "product_name": product["name"],
                    "product_price": product["price"],
                    "quantity": 1
                }
            else:
                page = random.choice(pages)
                event_type = "pageview"
                properties = {}
        
        elif random.random() < 0.1 and cart_items:  # 10% chance to checkout
            page = "/checkout"
            event_type = "checkout"
            total_amount = sum(item["price"] for item in cart_items)
            properties = {
                "cart_items": len(cart_items),
                "total_amount": total_amount,
                "payment_method": random.choice(["credit_card", "paypal", "apple_pay"])
            }
        
        else:  # Regular page navigation
            page = random.choice(pages)
            event_type = "pageview"
            properties = {}
        
        events.append({
            "session_id": session["session_id"],
            "client_id": session["client_id"],
            "user_id": session["user_id"],
            "page": page,
            "event_type": event_type,
            "timestamp": current_time,
            "properties": properties
        })
    
    return events

def simulate(num_sessions=20, seed_products_first=True):
    """Simulate clickstream events with product data"""
    products = ensure_products()
    if not products:
        print("No products available; aborting simulation.")
        return 0
    print(f"Simulating {num_sessions} sessions...")
    total_events = 0
    
    for i in range(num_sessions):
        session = create_session()
        events = simulate_session(session, random.randint(3, 8), products=products)
        
        for ev in events:
            ingest_event(ev)
            total_events += 1
        
        if (i + 1) % 10 == 0:
            print(f"Completed {i + 1} sessions...")
    
    return total_events

def simulate_realistic_ecommerce(num_sessions=50):
    """Simulate more realistic e-commerce behavior"""
    print("=== Realistic E-commerce Clickstream Simulation ===")
    products = ensure_products()
    if not products:
        print("No products available; aborting simulation.")
        return 0
    
    # Simulate different types of users
    user_types = [
        {"type": "browser", "sessions": int(num_sessions * 0.4), "avg_events": 4, "conversion_rate": 0.1},
        {"type": "shopper", "sessions": int(num_sessions * 0.3), "avg_events": 6, "conversion_rate": 0.3},
        {"type": "buyer", "sessions": int(num_sessions * 0.2), "avg_events": 8, "conversion_rate": 0.7},
        {"type": "returning", "sessions": int(num_sessions * 0.1), "avg_events": 10, "conversion_rate": 0.5}
    ]
    
    total_events = 0
    for user_type in user_types:
        print(f"Simulating {user_type['type']} users: {user_type['sessions']} sessions")
        
        for _ in range(user_type['sessions']):
            session = create_session()
            # Adjust behavior based on user type
            num_events = random.randint(
                user_type['avg_events'] - 2, 
                user_type['avg_events'] + 2
            )
            
            events = simulate_session(session, num_events, products=products)
            
            # Apply conversion rate
            if random.random() < user_type['conversion_rate']:
                # Add checkout event
                checkout_event = {
                    "session_id": session["session_id"],
                    "client_id": session["client_id"],
                    "user_id": session["user_id"],
                    "page": "/checkout",
                    "event_type": "purchase",
                    "timestamp": session["start_time"] + random.randint(300, 1800),
                    "properties": {
                        "order_id": f"order_{random.randint(1000, 9999)}",
                        "total_amount": random.randint(50, 500),
                        "payment_method": random.choice(["credit_card", "paypal", "apple_pay"])
                    }
                }
                events.append(checkout_event)
            
            for ev in events:
                ingest_event(ev)
                total_events += 1
    
    return total_events

if __name__ == "__main__":
    print("Choose simulation type:")
    print("1. Basic simulation (20 sessions)")
    print("2. Realistic e-commerce simulation (50 sessions)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        total = simulate_realistic_ecommerce(50)
        print(f"✅ Inserted {total} realistic e-commerce events across 50 sessions")
    else:
        total = simulate(20)
        print(f"✅ Inserted {total} events across 20 sessions")
