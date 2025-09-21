# review_and_fix_system.py - Comprehensive review and fix of the system
from db import get_db, users_col, events_col, analyses_col, sessions_col, api_keys_col
from bson import ObjectId
from datetime import datetime, timedelta
import random
import time
import json

def review_database_structure():
    """Review current database structure and identify issues"""
    print("🔍 Reviewing Database Structure...")
    
    db = get_db()
    collections = db.list_collection_names()
    print(f"Collections found: {collections}")
    
    # Check each collection
    for collection_name in collections:
        collection = db[collection_name]
        count = collection.count_documents({})
        print(f"  {collection_name}: {count} documents")
        
        if count > 0:
            # Show sample document
            sample = collection.find_one()
            print(f"    Sample fields: {list(sample.keys()) if sample else 'None'}")
            
            # Check for ID consistency issues
            if collection_name == "events":
                check_events_id_consistency(collection)
            elif collection_name == "users":
                check_users_structure(collection)
            elif collection_name == "analyses":
                check_analyses_structure(collection)

def check_events_id_consistency(events_collection):
    """Check ID consistency in events collection"""
    print("    Checking events ID consistency...")
    
    events = list(events_collection.find().limit(10))
    
    if not events:
        print("    No events found")
        return
    
    # Check user_id types
    user_id_types = set()
    session_id_types = set()
    
    for event in events:
        if event.get('user_id'):
            user_id_types.add(type(event['user_id']).__name__)
        if event.get('session_id'):
            session_id_types.add(type(event['session_id']).__name__)
    
    print(f"    User ID types: {user_id_types}")
    print(f"    Session ID types: {session_id_types}")
    
    # Check for null IDs
    null_user_ids = sum(1 for e in events if not e.get('user_id'))
    null_session_ids = sum(1 for e in events if not e.get('session_id'))
    
    print(f"    Events with null user_id: {null_user_ids}")
    print(f"    Events with null session_id: {null_session_ids}")

def check_users_structure(users_collection):
    """Check users collection structure"""
    print("    Checking users structure...")
    
    users = list(users_collection.find().limit(5))
    
    if not users:
        print("    No users found")
        return
    
    for user in users:
        print(f"    User: {user.get('username', 'N/A')} - ID: {user.get('_id')} (type: {type(user.get('_id'))})")

def check_analyses_structure(analyses_collection):
    """Check analyses collection structure"""
    print("    Checking analyses structure...")
    
    analyses = list(analyses_collection.find().limit(3))
    
    if not analyses:
        print("    No analyses found")
        return
    
    for analysis in analyses:
        print(f"    Analysis: {analysis.get('_id')} - User: {analysis.get('user_id')} (type: {type(analysis.get('user_id'))})")

def create_consistent_user_system():
    """Create a consistent user system with proper ID management"""
    print("\n👥 Creating Consistent User System...")
    
    # Clear existing data
    users_col().delete_many({})
    events_col().delete_many({})
    analyses_col().delete_many({})
    sessions_col().delete_many({})
    
    # Create test users with consistent structure
    test_users = [
        {
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": "alice123_hash",
            "role": "user",
            "profile": {
                "age_group": "25-34",
                "interests": ["electronics", "fashion"],
                "user_type": "frequent_buyer"
            },
            "created_at": datetime.utcnow()
        },
        {
            "username": "bob",
            "email": "bob@example.com", 
            "password_hash": "bob123_hash",
            "role": "user",
            "profile": {
                "age_group": "35-44",
                "interests": ["technology", "gaming"],
                "user_type": "tech_enthusiast"
            },
            "created_at": datetime.utcnow()
        },
        {
            "username": "charlie",
            "email": "charlie@example.com",
            "password_hash": "charlie123_hash", 
            "role": "user",
            "profile": {
                "age_group": "18-24",
                "interests": ["fashion", "lifestyle"],
                "user_type": "browser"
            },
            "created_at": datetime.utcnow()
        },
        {
            "username": "diana",
            "email": "diana@example.com",
            "password_hash": "diana123_hash",
            "role": "user", 
            "profile": {
                "age_group": "45-54",
                "interests": ["home", "food"],
                "user_type": "practical_shopper"
            },
            "created_at": datetime.utcnow()
        },
        {
            "username": "eve",
            "email": "eve@example.com",
            "password_hash": "eve123_hash",
            "role": "user",
            "profile": {
                "age_group": "25-34", 
                "interests": ["beauty", "fashion"],
                "user_type": "luxury_buyer"
            },
            "created_at": datetime.utcnow()
        }
    ]
    
    # Insert users and get their IDs
    user_docs = []
    for user_data in test_users:
        user_data["_id"] = ObjectId()
        user_docs.append(user_data)
    
    users_col().insert_many(user_docs)
    print(f"✅ Created {len(user_docs)} users with consistent ObjectId structure")
    
    return user_docs

def create_product_catalog():
    """Create a comprehensive product catalog"""
    print("\n🛍️ Creating Product Catalog...")
    
    products = [
        # Electronics
        {"name": "MacBook Pro 14", "category": "electronics", "subcategory": "laptop", "price": 2000, "brand": "Apple", "tags": ["laptop", "professional", "high-end"]},
        {"name": "Dell XPS 13", "category": "electronics", "subcategory": "laptop", "price": 1200, "brand": "Dell", "tags": ["laptop", "business", "portable"]},
        {"name": "iPhone 15 Pro", "category": "electronics", "subcategory": "phone", "price": 999, "brand": "Apple", "tags": ["phone", "premium", "camera"]},
        {"name": "Samsung Galaxy S23", "category": "electronics", "subcategory": "phone", "price": 899, "brand": "Samsung", "tags": ["phone", "android", "camera"]},
        {"name": "AirPods Pro", "category": "electronics", "subcategory": "audio", "price": 249, "brand": "Apple", "tags": ["headphones", "wireless", "noise-canceling"]},
        
        # Fashion
        {"name": "Nike Air Max 270", "category": "fashion", "subcategory": "shoes", "price": 150, "brand": "Nike", "tags": ["sneakers", "sport", "casual"]},
        {"name": "Levi's 501 Jeans", "category": "fashion", "subcategory": "pants", "price": 80, "brand": "Levi's", "tags": ["jeans", "classic", "denim"]},
        {"name": "Zara Blazer", "category": "fashion", "subcategory": "jacket", "price": 120, "brand": "Zara", "tags": ["blazer", "formal", "work"]},
        {"name": "Ray-Ban Aviator", "category": "fashion", "subcategory": "accessories", "price": 180, "brand": "Ray-Ban", "tags": ["sunglasses", "classic", "style"]},
        
        # Home & Kitchen
        {"name": "Instant Pot", "category": "home", "subcategory": "kitchen", "price": 99, "brand": "Instant Pot", "tags": ["cooker", "pressure", "kitchen"]},
        {"name": "Dyson V15 Vacuum", "category": "home", "subcategory": "cleaning", "price": 699, "brand": "Dyson", "tags": ["vacuum", "cordless", "premium"]},
        {"name": "IKEA Desk Lamp", "category": "home", "subcategory": "furniture", "price": 25, "brand": "IKEA", "tags": ["lamp", "desk", "modern"]},
        
        # Food & Beverages
        {"name": "Starbucks Coffee Beans", "category": "food", "subcategory": "beverages", "price": 15, "brand": "Starbucks", "tags": ["coffee", "beans", "premium"]},
        {"name": "Organic Green Tea", "category": "food", "subcategory": "beverages", "price": 12, "brand": "Twinings", "tags": ["tea", "organic", "healthy"]},
        {"name": "Artisan Chocolate", "category": "food", "subcategory": "snacks", "price": 8, "brand": "Lindt", "tags": ["chocolate", "premium", "gift"]},
        
        # Beauty & Health
        {"name": "L'Oreal Foundation", "category": "beauty", "subcategory": "makeup", "price": 35, "brand": "L'Oreal", "tags": ["foundation", "makeup", "beauty"]},
        {"name": "Olay Moisturizer", "category": "beauty", "subcategory": "skincare", "price": 28, "brand": "Olay", "tags": ["moisturizer", "skincare", "anti-aging"]},
        {"name": "Oral-B Electric Toothbrush", "category": "health", "subcategory": "oral_care", "price": 89, "brand": "Oral-B", "tags": ["toothbrush", "electric", "dental"]}
    ]
    
    # Add IDs and timestamps
    for product in products:
        product["_id"] = ObjectId()
        product["created_at"] = datetime.utcnow()
        product["in_stock"] = True
        product["rating"] = round(random.uniform(3.5, 5.0), 1)
        product["reviews_count"] = random.randint(10, 500)
    
    # Clear existing products
    db = get_db()
    if "products" in db.list_collection_names():
        db.products.drop()
    
    db.products.insert_many(products)
    print(f"✅ Created {len(products)} products with detailed information")
    
    return products

def generate_realistic_user_behavior(users, products):
    """Generate realistic user behavior with product interactions"""
    print("\n🎭 Generating Realistic User Behavior...")
    
    events = []
    current_time = int(time.time()) - 86400  # Start 24 hours ago
    
    # Define user behavior patterns
    behavior_patterns = {
        "frequent_buyer": {
            "session_frequency": 0.8,  # 80% chance to have multiple sessions
            "product_view_rate": 0.7,  # 70% chance to view products
            "purchase_rate": 0.4,      # 40% chance to purchase
            "avg_session_length": 8,   # 8 events per session
            "preferred_categories": ["electronics", "fashion"]
        },
        "tech_enthusiast": {
            "session_frequency": 0.6,
            "product_view_rate": 0.9,
            "purchase_rate": 0.3,
            "avg_session_length": 12,
            "preferred_categories": ["electronics"]
        },
        "browser": {
            "session_frequency": 0.3,
            "product_view_rate": 0.5,
            "purchase_rate": 0.1,
            "avg_session_length": 4,
            "preferred_categories": ["fashion", "beauty"]
        },
        "practical_shopper": {
            "session_frequency": 0.5,
            "product_view_rate": 0.6,
            "purchase_rate": 0.5,
            "avg_session_length": 6,
            "preferred_categories": ["home", "food"]
        },
        "luxury_buyer": {
            "session_frequency": 0.4,
            "product_view_rate": 0.8,
            "purchase_rate": 0.6,
            "avg_session_length": 10,
            "preferred_categories": ["fashion", "beauty", "electronics"]
        }
    }
    
    for user in users:
        user_id = user["_id"]  # Keep as ObjectId
        user_type = user["profile"]["user_type"]
        behavior = behavior_patterns.get(user_type, behavior_patterns["browser"])
        
        # Generate multiple sessions for this user
        num_sessions = random.randint(1, 5) if random.random() < behavior["session_frequency"] else 1
        
        for session_num in range(num_sessions):
            session_id = f"session_{str(user_id)[-6:]}_{session_num}_{int(time.time())}"
            client_id = f"client_{str(user_id)[-6:]}_{session_num}"
            
            # Generate session events
            session_events = generate_session_events(
                user_id, session_id, client_id, 
                user, products, behavior, current_time
            )
            
            events.extend(session_events)
            current_time += random.randint(3600, 14400)  # 1-4 hours between sessions
    
    # Insert all events
    events_col().insert_many(events)
    print(f"✅ Generated {len(events)} events with realistic user behavior")
    
    return events

def generate_session_events(user_id, session_id, client_id, user, products, behavior, start_time):
    """Generate events for a single session"""
    events = []
    current_time = start_time
    
    # Start with home page
    events.append({
        "user_id": user_id,  # ObjectId
        "session_id": session_id,  # String
        "client_id": client_id,  # String
        "page": "/home",
        "event_type": "pageview",
        "timestamp": datetime.utcfromtimestamp(current_time),
        "properties": {
            "referrer": "direct",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    })
    
    # Generate additional events based on behavior pattern
    num_events = random.randint(
        max(1, behavior["avg_session_length"] - 3),
        behavior["avg_session_length"] + 3
    )
    
    viewed_products = set()
    cart_items = []
    
    for i in range(num_events - 1):
        current_time += random.randint(10, 300)  # 10s to 5min between events
        
        # Determine next action based on behavior
        action = determine_next_action(i, behavior, viewed_products, cart_items)
        
        if action["type"] == "category_browse":
            category = random.choice(behavior["preferred_categories"])
            events.append({
                "user_id": user_id,
                "session_id": session_id,
                "client_id": client_id,
                "page": f"/category/{category}",
                "event_type": "pageview",
                "timestamp": datetime.utcfromtimestamp(current_time),
                "properties": {
                    "category": category,
                    "source": "navigation"
                }
            })
            
        elif action["type"] == "product_view" and random.random() < behavior["product_view_rate"]:
            # Select product based on user preferences
            preferred_products = [p for p in products if p["category"] in behavior["preferred_categories"]]
            if not preferred_products:
                preferred_products = products
            
            product = random.choice(preferred_products)
            viewed_products.add(str(product["_id"]))
            
            events.append({
                "user_id": user_id,
                "session_id": session_id,
                "client_id": client_id,
                "page": f"/product/{product['_id']}",
                "event_type": "pageview",
                "timestamp": datetime.utcfromtimestamp(current_time),
                "properties": {
                    "product_id": str(product["_id"]),
                    "product_name": product["name"],
                    "product_category": product["category"],
                    "product_subcategory": product["subcategory"],
                    "product_price": product["price"],
                    "product_brand": product["brand"],
                    "product_rating": product["rating"],
                    "source": "category" if viewed_products else "search"
                }
            })
            
        elif action["type"] == "search":
            search_terms = get_search_terms_for_user(user, products)
            search_term = random.choice(search_terms)
            
            events.append({
                "user_id": user_id,
                "session_id": session_id,
                "client_id": client_id,
                "page": "/search",
                "event_type": "search",
                "timestamp": datetime.utcfromtimestamp(current_time),
                "properties": {
                    "search_term": search_term,
                    "results_count": random.randint(5, 50)
                }
            })
            
        elif action["type"] == "add_to_cart" and viewed_products and random.random() < 0.3:
            product_id = random.choice(list(viewed_products))
            product = next(p for p in products if str(p["_id"]) == product_id)
            cart_items.append(product)
            
            events.append({
                "user_id": user_id,
                "session_id": session_id,
                "client_id": client_id,
                "page": "/cart",
                "event_type": "add_to_cart",
                "timestamp": datetime.utcfromtimestamp(current_time),
                "properties": {
                    "product_id": product_id,
                    "product_name": product["name"],
                    "product_price": product["price"],
                    "quantity": 1,
                    "cart_total": sum(item["price"] for item in cart_items)
                }
            })
            
        elif action["type"] == "checkout" and cart_items and random.random() < behavior["purchase_rate"]:
            total_amount = sum(item["price"] for item in cart_items)
            
            events.append({
                "user_id": user_id,
                "session_id": session_id,
                "client_id": client_id,
                "page": "/checkout",
                "event_type": "purchase",
                "timestamp": datetime.utcfromtimestamp(current_time),
                "properties": {
                    "order_id": f"order_{random.randint(10000, 99999)}",
                    "total_amount": total_amount,
                    "items_count": len(cart_items),
                    "payment_method": random.choice(["credit_card", "paypal", "apple_pay"]),
                    "shipping_address": "123 Main St, City, State",
                    "billing_address": "123 Main St, City, State"
                }
            })
            
        else:
            # Regular page navigation
            pages = ["/home", "/category", "/search", "/cart", "/account"]
            page = random.choice(pages)
            
            events.append({
                "user_id": user_id,
                "session_id": session_id,
                "client_id": client_id,
                "page": page,
                "event_type": "pageview",
                "timestamp": datetime.utcfromtimestamp(current_time),
                "properties": {}
            })
    
    return events

def determine_next_action(step, behavior, viewed_products, cart_items):
    """Determine the next action based on user behavior and current state"""
    if step == 0:
        return {"type": "category_browse"}
    elif step == 1 and random.random() < 0.7:
        return {"type": "product_view"}
    elif len(viewed_products) > 0 and random.random() < 0.3:
        return {"type": "add_to_cart"}
    elif len(cart_items) > 0 and random.random() < 0.2:
        return {"type": "checkout"}
    elif random.random() < 0.3:
        return {"type": "search"}
    elif random.random() < 0.4:
        return {"type": "product_view"}
    else:
        return {"type": "category_browse"}

def get_search_terms_for_user(user, products):
    """Get relevant search terms based on user profile"""
    user_interests = user["profile"]["interests"]
    user_type = user["profile"]["user_type"]
    
    search_terms = []
    
    # Add terms based on interests
    for interest in user_interests:
        if interest == "electronics":
            search_terms.extend(["laptop", "phone", "headphones", "tablet"])
        elif interest == "fashion":
            search_terms.extend(["shoes", "jeans", "dress", "jacket"])
        elif interest == "beauty":
            search_terms.extend(["makeup", "skincare", "perfume", "cosmetics"])
        elif interest == "home":
            search_terms.extend(["furniture", "decor", "kitchen", "cleaning"])
        elif interest == "food":
            search_terms.extend(["coffee", "tea", "chocolate", "organic"])
    
    # Add terms based on user type
    if user_type == "tech_enthusiast":
        search_terms.extend(["gaming", "computer", "gadget", "tech"])
    elif user_type == "luxury_buyer":
        search_terms.extend(["premium", "designer", "luxury", "high-end"])
    elif user_type == "practical_shopper":
        search_terms.extend(["affordable", "value", "practical", "useful"])
    
    # Add some general terms
    search_terms.extend(["gift", "sale", "new", "popular", "trending"])
    
    return search_terms

def verify_id_consistency():
    """Verify ID consistency across the system"""
    print("\n🔍 Verifying ID Consistency...")
    
    # Check events
    events = list(events_col().find().limit(10))
    print(f"Sample events ({len(events)}):")
    
    for i, event in enumerate(events):
        print(f"  Event {i+1}:")
        print(f"    User ID: {event.get('user_id')} (type: {type(event.get('user_id'))})")
        print(f"    Session ID: {event.get('session_id')} (type: {type(event.get('session_id'))})")
        print(f"    Page: {event.get('page')}")
        print(f"    Event Type: {event.get('event_type')}")
        if event.get('properties', {}).get('product_id'):
            print(f"    Product ID: {event.get('properties', {}).get('product_id')}")
        print()
    
    # Check for consistency issues
    user_id_types = set()
    session_id_types = set()
    
    for event in events:
        if event.get('user_id'):
            user_id_types.add(type(event['user_id']).__name__)
        if event.get('session_id'):
            session_id_types.add(type(event['session_id']).__name__)
    
    print(f"User ID types found: {user_id_types}")
    print(f"Session ID types found: {session_id_types}")
    
    # Check for null IDs
    all_events = list(events_col().find())
    null_user_ids = sum(1 for e in all_events if not e.get('user_id'))
    null_session_ids = sum(1 for e in all_events if not e.get('session_id'))
    
    print(f"Events with null user_id: {null_user_ids}/{len(all_events)}")
    print(f"Events with null session_id: {null_session_ids}/{len(all_events)}")
    
    return len(user_id_types) == 1 and null_user_ids == 0 and null_session_ids == 0

def main():
    """Main function to review and fix the system"""
    print("🚀 Clickstream System Review and Fix")
    print("=" * 50)
    
    # 1. Review current state
    review_database_structure()
    
    # 2. Create consistent user system
    users = create_consistent_user_system()
    
    # 3. Create product catalog
    products = create_product_catalog()
    
    # 4. Generate realistic user behavior
    events = generate_realistic_user_behavior(users, products)
    
    # 5. Verify ID consistency
    consistency_ok = verify_id_consistency()
    
    # 6. Summary
    print("\n📊 System Summary:")
    print(f"  Users: {len(users)}")
    print(f"  Products: {len(products)}")
    print(f"  Events: {len(events)}")
    print(f"  ID Consistency: {'✅ PASS' if consistency_ok else '❌ FAIL'}")
    
    if consistency_ok:
        print("\n🎉 System is now consistent and ready for analysis!")
    else:
        print("\n⚠️ System still has consistency issues that need to be addressed.")

if __name__ == "__main__":
    main()
