# simulate_clickstream.py
from ingest import ingest_event
from db import get_db, users_col, sessions_col
from bson import ObjectId
import random, time
from datetime import datetime, timedelta

# Product data for realistic clickstream simulation
PRODUCTS = [
    # ---- Computers ----
        {"name": "Lenovo ThinkPad X1", "category": "computer", "price": 1500, "tags": ["electronics","laptop"]},
        {"name": "Asus ROG Strix", "category": "computer", "price": 1800, "tags": ["electronics","gaming","laptop"]},
        {"name": "HP Spectre x360", "category": "computer", "price": 1400, "tags": ["electronics","laptop"]},
        {"name": "Microsoft Surface Laptop 5", "category": "computer", "price": 1600, "tags": ["electronics","portable"]},
        {"name": "Acer Aspire 7", "category": "computer", "price": 900, "tags": ["electronics","budget"]},
        {"name": "Alienware M16", "category": "computer", "price": 2200, "tags": ["electronics","gaming"]},
        
        # ---- Phones ----
        {"name": "Google Pixel 8", "category": "phone", "price": 799, "tags": ["electronics","mobile"]},
        {"name": "OnePlus 11", "category": "phone", "price": 699, "tags": ["electronics","mobile"]},
        {"name": "Xiaomi Mi 13", "category": "phone", "price": 650, "tags": ["electronics","mobile"]},
        {"name": "Oppo Find X6", "category": "phone", "price": 720, "tags": ["electronics","mobile"]},
        {"name": "Sony Xperia 5 V", "category": "phone", "price": 950, "tags": ["electronics","camera"]},
        {"name": "Nokia G60", "category": "phone", "price": 400, "tags": ["electronics","budget"]},
        
        # ---- Drinks ----
        {"name": "Coca Cola Bottle", "category": "drink", "price": 2.0, "tags": ["beverage","cold"]},
        {"name": "Green Tea", "category": "drink", "price": 2.5, "tags": ["beverage","hot"]},
        {"name": "Latte Coffee", "category": "drink", "price": 3.5, "tags": ["beverage","hot"]},
        {"name": "Orange Juice", "category": "drink", "price": 2.8, "tags": ["beverage","fruit"]},
        {"name": "Mineral Water", "category": "drink", "price": 1.0, "tags": ["beverage","cold"]},
        {"name": "Energy Drink Monster", "category": "drink", "price": 2.2, "tags": ["beverage","energy"]},
        
        # ---- Food ----
        {"name": "Burger Beef", "category": "food", "price": 8, "tags": ["meal","fastfood"]},
        {"name": "Pasta Carbonara", "category": "food", "price": 12, "tags": ["meal","italian"]},
        {"name": "Steak Medium Rare", "category": "food", "price": 25, "tags": ["meal","western"]},
        {"name": "Chicken Curry", "category": "food", "price": 14, "tags": ["meal","asian"]},
        {"name": "Fried Rice", "category": "food", "price": 9, "tags": ["meal","asian"]},
        {"name": "Salmon Sushi Roll", "category": "food", "price": 18, "tags": ["meal","japanese"]},
        {"name": "Vegan Salad Bowl", "category": "food", "price": 11, "tags": ["meal","healthy"]},
        
        # ---- Glasses ----
        {"name": "Oakley Sport Glasses", "category": "glasses", "price": 120, "tags": ["fashion","sport"]},
        {"name": "Gucci Designer Glasses", "category": "glasses", "price": 350, "tags": ["fashion","luxury"]},
        {"name": "Blue Light Blocking Glasses", "category": "glasses", "price": 80, "tags": ["vision","work"]},
        {"name": "Kids Reading Glasses", "category": "glasses", "price": 30, "tags": ["vision","kids"]},
        
        # ---- Pants ----
        {"name": "Cargo Pants Green", "category": "pants", "price": 50, "tags": ["clothing","casual"]},
        {"name": "Jogger Pants Black", "category": "pants", "price": 45, "tags": ["clothing","sport"]},
        {"name": "Slim Fit Jeans", "category": "pants", "price": 55, "tags": ["clothing","casual"]},
        {"name": "Khaki Pants Beige", "category": "pants", "price": 65, "tags": ["clothing","formal"]},
        
        # ---- Shoes ----
        {"name": "Adidas Ultraboost", "category": "shoes", "price": 160, "tags": ["clothing","sport"]},
        {"name": "Converse Chuck Taylor", "category": "shoes", "price": 70, "tags": ["clothing","casual"]},
        {"name": "Puma Running Shoes", "category": "shoes", "price": 95, "tags": ["clothing","sport"]},
        {"name": "Reebok Classic", "category": "shoes", "price": 85, "tags": ["clothing","casual"]},
        {"name": "Timberland Boots", "category": "shoes", "price": 200, "tags": ["clothing","outdoor"]},
        
        # ---- Shirts ----
        {"name": "Polo Shirt Blue", "category": "shirt", "price": 25, "tags": ["clothing","casual"]},
        {"name": "Hoodie Black", "category": "shirt", "price": 45, "tags": ["clothing","casual"]},
        {"name": "Sweater Grey", "category": "shirt", "price": 40, "tags": ["clothing","casual"]},
        {"name": "Flannel Shirt Red", "category": "shirt", "price": 30, "tags": ["clothing","casual"]},
        {"name": "Silk Shirt", "category": "shirt", "price": 70, "tags": ["clothing","luxury"]},
        {"name": "Denim Jacket", "category": "shirt", "price": 80, "tags": ["clothing","casual"]},
        {"name": "Winter Coat", "category": "shirt", "price": 120, "tags": ["clothing","outerwear"]},
        {"name": "Trench Coat", "category": "shirt", "price": 150, "tags": ["clothing","formal"]},
]

# Enhanced pages with product-specific pages
pages = ["/home", "/category", "/search", "/checkout", "/cart"]
session_duration = 1800  # 30 minutes in seconds

def seed_products():
    """Seed products into MongoDB"""
    db = get_db()
    products_collection = db.products
    
    # Clear existing products
    products_collection.delete_many({})
    
    # Add products with IDs and timestamps
    for p in PRODUCTS:
        p["_id"] = ObjectId()
        p["created_at"] = datetime.utcnow()
    
    products_collection.insert_many(PRODUCTS)
    print(f"Seeded {len(PRODUCTS)} products into MongoDB")
    return PRODUCTS

def get_random_product():
    """Get a random product from the products list"""
    return random.choice(PRODUCTS)

def get_products_by_category(category):
    """Get products filtered by category"""
    return [p for p in PRODUCTS if p["category"] == category]

def get_or_create_test_users():
    """Get existing users or create test users for simulation"""
    users = list(users_col().find({}))
    
    if not users:
        print("No users found, creating test users...")
        # Create some test users
        test_users = [
            {"username": "alice", "email": "alice@example.com", "password": "alice123"},
            {"username": "bob", "email": "bob@example.com", "password": "bob123"},
            {"username": "charlie", "email": "charlie@example.com", "password": "charlie123"},
            {"username": "diana", "email": "diana@example.com", "password": "diana123"},
            {"username": "eve", "email": "eve@example.com", "password": "eve123"}
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

def simulate_session(session, num_events=5):
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
            product = get_random_product()
            viewed_products.add(product["name"])
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
                product_name = random.choice(list(viewed_products))
                product = next(p for p in PRODUCTS if p["name"] == product_name)
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
    if seed_products_first:
        print("Seeding products...")
        seed_products()
    
    print(f"Simulating {num_sessions} sessions...")
    total_events = 0
    
    for i in range(num_sessions):
        session = create_session()
        events = simulate_session(session, random.randint(3, 8))
        
        for ev in events:
            ingest_event(ev)
            total_events += 1
        
        if (i + 1) % 10 == 0:
            print(f"Completed {i + 1} sessions...")
    
    return total_events

def simulate_realistic_ecommerce(num_sessions=50):
    """Simulate more realistic e-commerce behavior"""
    print("=== Realistic E-commerce Clickstream Simulation ===")
    
    # Seed products first
    seed_products()
    
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
            
            events = simulate_session(session, num_events)
            
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
