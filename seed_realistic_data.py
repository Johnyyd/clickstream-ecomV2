"""
seed_realistic_data.py

Seed realistic, customer-like data into MongoDB while preserving the current schema.
- Uses ingest_event() to ensure event documents match production schema
- Generates plausible funnels and timings
- Spreads traffic across hours/days and multiple users
- Grounds product interactions on the products catalog

Usage examples (PowerShell):
  # Seed 7 days of data for 25 users, ~5 sessions/day, ~7 events/session
  venv/Scripts/python.exe seed_realistic_data.py --days 7 --user-count 25 --sessions-per-user 5 --avg-events 7

  # Seed for one specific user (created if missing)
  venv/Scripts/python.exe seed_realistic_data.py --username alice --days 5 --sessions-per-user 3 --avg-events 6

Notes:
- Adds a harmless marker in properties.source = "realistic_seed" to help optional filtering. Schema remains compatible.
- If your products collection is empty, run seed_products.py first or pass --seed-products.
"""
from __future__ import annotations

import argparse
import random
import pytz
from datetime import datetime, timedelta
from typing import List, Optional

from bson import ObjectId

from app.core.db_sync import users_col, products_col, sessions_col, carts_col
from seed_products import slugify
from ingest import ingest_event
from app.services.auth import create_user

PAGES = ["/home", "/category", "/search", "/p", "/cart", "/checkout"]


def ensure_products(seed_products_first: bool) -> int:
    if seed_products_first:
        # Try user's updated seeder first (seed_more_products), then fallback
        try:
            from seed_products import seed_more_products as sp
            sp()
        except Exception:
            try:
                from seed_products import seed_products as sp2
                sp2()
            except Exception:
                pass
    return products_col().count_documents({})


def ensure_users(target_username: Optional[str], count: int) -> List[ObjectId]:
    ids: List[ObjectId] = []
    if target_username:
        u = users_col().find_one({"username": target_username})
        if not u:
            email = f"{target_username}@example.com"
            pw = f"{target_username}123"
            created = create_user(target_username, email, pw)
            # create_user returns user dict or {"error": ...}
            if isinstance(created, dict) and created.get("_id"):
                u = created
            else:
                u = users_col().find_one({"username": target_username})
        ids.append(u["_id"])  # type: ignore[index]
        return ids

    # Reuse existing users; top up with new ones until reaching 'count'
    existing = list(users_col().find({}, {"_id": 1, "username": 1}))
    pool = [u["_id"] for u in existing]
    idx = 1
    while len(pool) < count:
        uname = f"customer{idx:03d}"
        idx += 1
        try:
            created = create_user(uname, f"{uname}@example.com", f"{uname}123")
            if isinstance(created, dict) and created.get("_id"):
                pool.append(created["_id"])  # already ObjectId from repo
            else:
                u = users_col().find_one({"username": uname})
                if u:
                    pool.append(u["_id"])
        except Exception:
            u = users_col().find_one({"username": uname})
            if u:
                pool.append(u["_id"])
    return pool[:count]


def emit_event(user_id, session_id, ts, page, event_type, props=None):
    ev = {
        "user_id": str(user_id),
        "session_id": session_id,
        "timestamp": int(ts),
        "page": page,
        "event_type": event_type,
        "properties": {"source": "realistic_seed", **(props or {})},
    }
    ingest_event(ev)


def realistic_product(products):
    # Weighted by rough popularity: computers/phones more popular
    weights = []
    for p in products:
        cat = p.get("category")
        if cat in ("computer", "phone"):
            w = 4
        elif cat in ("shoes", "shirt", "pants"):
            w = 2
        else:
            w = 1
        weights.append(w)
    return random.choices(products, weights=weights, k=1)[0]


def _update_user_cart(user_id: ObjectId, product_id: ObjectId, delta_qty: int = 1):
    try:
        # Increment quantity for the product in user's cart
        pid = str(product_id)
        col = carts_col()
        doc = col.find_one({"user_id": user_id})
        if not doc:
            col.insert_one({"user_id": user_id, "items": [{"product_id": pid, "quantity": max(1, int(delta_qty))}]})
            return
        items = doc.get("items", [])
        found = False
        for it in items:
            if str(it.get("product_id")) == pid:
                it["quantity"] = max(1, int(it.get("quantity") or 0) + int(delta_qty))
                found = True
                break
        if not found:
            items.append({"product_id": pid, "quantity": max(1, int(delta_qty))})
        col.update_one({"_id": doc["_id"]}, {"$set": {"items": items}})
    except Exception:
        pass


def ensure_browsing_session(session_id: str, user_id: ObjectId, start_ts: int) -> bool:
    """Upsert a browsing session document matching ingest.py behavior.
    Query by session_id field (not _id) to ensure consistency with runtime ingestion.
    Returns True if the upsert was acknowledged, False otherwise.
    """
    try:
        ts = datetime.fromtimestamp(start_ts, tz=pytz.UTC)
        res = sessions_col().update_one(
            {"session_id": session_id},  # Match ingest.py: query by session_id field
            {
                "$setOnInsert": {
                    "session_id": session_id,
                    "user_id": user_id,
                    # Don't set pages here - will be populated by ingest_event
                },
                "$max": {"last_event_at": ts},
                "$min": {"first_event_at": ts},
                "$inc": {"event_count": 0},
            },
            upsert=True,
        )
        return bool(res.acknowledged)
    except Exception as e:
        print(f"[seed] ensure_browsing_session error for {session_id}: {e}")
        return False


def generate_session_for_user(user_id: ObjectId, start_ts: int, avg_events: int, products: list[dict], persona: dict = None):
    """Generate a realistic session with plausible navigation and conversion behavior."""
    sid = str(ObjectId())
    current_ts = start_ts
    now_utc_ts = int(datetime.now(pytz.UTC).timestamp())
    if current_ts > now_utc_ts:
        current_ts = now_utc_ts

    # Use persona to adjust behavior
    if not persona:
        persona = {"name": "normal", "browse_rate": 0.35, "product_view_rate": 0.35, "cart_rate": 0.18, "checkout_rate": 0.12}
    
    # First event: home with varied entry points
    ensure_browsing_session(sid, user_id, current_ts)
    entry_points = [
        ("/home", "pageview", {"referrer": random.choice(["direct","email","social","ads","google","facebook"])}),
        ("/search", "search", {"search_term": random.choice(["laptop","phone","coffee","shoes","shirt"]), "referrer": "google"}),
        (f"/category?category={random.choice([p.get('category') for p in products])}", "pageview", {"referrer": "social"}),
    ]
    entry = random.choices(entry_points, weights=[0.6, 0.25, 0.15], k=1)[0]
    emit_event(user_id, sid, current_ts, entry[0], entry[1], entry[2])

    viewed_product_ids: list[str] = []
    cart = []

    # More varied events count based on persona
    if persona["name"] == "bouncer":
        n_events = random.randint(1, 3)  # Quick exit
    elif persona["name"] == "browser":
        n_events = random.randint(avg_events - 2, avg_events)  # Normal browsing
    elif persona["name"] == "shopper":
        n_events = random.randint(avg_events, avg_events + 3)  # More engaged
    elif persona["name"] == "power_buyer":
        n_events = random.randint(avg_events + 2, avg_events + 5)  # Very engaged
    else:
        n_events = max(3, random.randint(avg_events - 2, avg_events + 2))

    for i in range(1, n_events):
        # More realistic spacing based on user behavior
        # Use persona-specific timing between events
        current_ts += random.randint(persona.get("event_time_min", 15), 
                                   persona.get("event_time_max", 120))
        # Do not let events drift into the future
        if current_ts > now_utc_ts:
            current_ts = now_utc_ts
        
        r = random.random()

        if r < persona["browse_rate"]:  # category/search discoverability
            if random.random() < 0.55:
                category = random.choice([p.get("category") for p in products])
                emit_event(
                    user_id,
                    sid,
                    current_ts,
                    f"/category?category={category}",
                    "pageview",
                    {"category": category},
                )
            else:
                term = random.choice(["laptop","phone","coffee","shoes","shirt","pizza","sushi"]) 
                emit_event(user_id, sid, current_ts, "/search", "search", {"search_term": term})
        elif r < (persona["browse_rate"] + persona["product_view_rate"]):  # view product
            p = realistic_product(products)
            viewed_product_ids.append(str(p["_id"]))
            emit_event(
                user_id,
                sid,
                current_ts,
                f"/p/{slugify(p.get('name') or str(p['_id']))}?id={str(p['_id'])}",
                "pageview",
                {
                    "product_id": str(p["_id"]),
                    "product_name": p["name"],
                    "product_category": p["category"],
                    "product_price": p["price"],
                },
            )
        elif r < (persona["browse_rate"] + persona["product_view_rate"] + persona["cart_rate"]):  # add to cart
            if viewed_product_ids:
                prod_id = random.choice(viewed_product_ids)
                p = next((pp for pp in products if str(pp["_id"]) == prod_id), None)
                if p:
                    cart.append(p)
                    _update_user_cart(user_id, p["_id"], 1)
                    emit_event(
                        user_id,
                        sid,
                        current_ts,
                        "/cart",
                        "add_to_cart",
                        {
                            "product_id": str(p["_id"]),
                            "product_name": p["name"],
                            "product_price": p["price"],
                            "quantity": 1,
                        },
                    )
            else:
                emit_event(user_id, sid, current_ts, "/home", "pageview", None)
        else:  # checkout / purchase path
            if cart:
                # Decide to attempt checkout with a probability influenced by persona
                attempt_checkout = random.random() < max(0.35, persona.get("checkout_rate", 0.1) + 0.15)
                if attempt_checkout:
                    # Emit checkout event
                    total = sum(item["price"] for item in cart)
                    # Include product_ids in checkout for downstream analytics
                    checkout_product_ids = [str(item["_id"]) for item in cart]
                    emit_event(
                        user_id,
                        sid,
                        current_ts,
                        "/checkout",
                        "checkout",
                        {
                            "cart_items": len(cart),
                            "total_amount": round(total, 2),
                            "product_ids": checkout_product_ids,
                        },
                    )
                    # Small delay then purchase with high probability
                    if random.random() < 0.85:
                        current_ts += random.randint(2, 10)
            if current_ts > now_utc_ts:
                current_ts = now_utc_ts
                # Choose a primary product_id for the purchase event to ensure ALS can use it
                primary_product = max(cart, key=lambda x: x.get("price", 0)) if cart else None
                primary_product_id = str(primary_product["_id"]) if primary_product else None
                emit_event(
                    user_id,
                    sid,
                    current_ts,
                    "/order-success",
                    "purchase",
                    {
                        "cart_items": len(cart),
                        "total_amount": round(total, 2),
                        "payment_method": random.choice(["credit_card","paypal","apple_pay"]),
                        "order_id": f"order_{random.randint(1000,9999)}",
                        # Primary product for collaborative filtering
                        **({"product_id": primary_product_id} if primary_product_id else {}),
                    },
                )
                # Clear persistent cart upon purchase
                try:
                    carts_col().update_one({"user_id": user_id}, {"$set": {"items": []}}, upsert=True)
                except Exception:
                    pass
                cart.clear()
            else:
                # Keep browsing without checkout
                if random.random() < 0.5:
                    emit_event(user_id, sid, current_ts, "/home", "pageview", None)
                else:
                    cat = random.choice([p.get("category") for p in products])
                    emit_event(
                        user_id,
                        sid,
                        current_ts,
                        f"/category?category={cat}",
                        "pageview",
                        {"category": cat},
                    )
    else:
        # No items yet, continue browsing
        if random.random() < 0.5:
            emit_event(user_id, sid, current_ts, "/home", "pageview", None)
        else:
            cat = random.choice([p.get("category") for p in products])
            emit_event(
                user_id,
                sid,
                current_ts,
                f"/category?category={cat}",
                "pageview",
                {"category": cat},
            )

    # End-of-session finalization: convert some lingering carts
    if cart and random.random() < 0.25:
        total = sum(item["price"] for item in cart)
        current_ts += random.randint(5, 30)
        if current_ts > now_utc_ts:
            current_ts = now_utc_ts
        # Include product_ids in checkout for downstream analytics
        emit_event(
            user_id,
            sid,
            current_ts,
            "/checkout",
            "checkout",
            {
                "cart_items": len(cart),
                "total_amount": round(total, 2),
                "product_ids": [str(item["_id"]) for item in cart],
            },
        )
        if random.random() < 0.9:
            current_ts += random.randint(2, 10)
            primary_product = max(cart, key=lambda x: x.get("price", 0)) if cart else None
            primary_product_id = str(primary_product["_id"]) if primary_product else None
            emit_event(
                user_id,
                sid,
                current_ts,
                "/order-success",
                "purchase",
                {
                    "cart_items": len(cart),
                    "total_amount": round(total, 2),
                    "payment_method": random.choice(["credit_card","paypal","apple_pay"]),
                    "order_id": f"order_{random.randint(1000,9999)}",
                    **({"product_id": primary_product_id} if primary_product_id else {}),
                },
            )
            try:
                carts_col().update_one({"user_id": user_id}, {"$set": {"items": []}}, upsert=True)
            except Exception:
                pass
            cart.clear()


def seed_event_for_users(user_ids: List[ObjectId], days: int, sessions_per_user: int, avg_events: int, seed_products_first: bool):
    product_count = ensure_products(seed_products_first)
    if product_count == 0:
        print("No products found. Please seed products first.")
        return 0
    products = list(products_col().find({}))

    now = datetime.now(pytz.UTC)
    total_est = 0
    
    # More diverse user personas with realistic behavior patterns
    PERSONAS = [
        # Bouncer: 0.5% for target bounce rate (1 event only)
        {"name": "bouncer", "weight": 0.005, "extra_sessions": 0, "avg_events": 1, 
         "browse_rate": 1.0, "product_view_rate": 0.0, "cart_rate": 0.0, "checkout_rate": 0.0},
        
        # Product Browsers: High product view rate (40%)
        {"name": "product_browser", "weight": 0.40, "extra_sessions": 0, "avg_events": max(6, avg_events - 1),
         "browse_rate": 0.15, "product_view_rate": 0.70, "cart_rate": 0.10, "checkout_rate": 0.05},
        
        # Window Shoppers: Browse products but rarely buy (25%)
        {"name": "window_shopper", "weight": 0.25, "extra_sessions": 2, "avg_events": max(8, avg_events),
         "browse_rate": 0.20, "product_view_rate": 0.60, "cart_rate": 0.15, "checkout_rate": 0.05},
        
        # Active Shoppers: View products and add to cart (20%)
        {"name": "shopper", "weight": 0.20, "extra_sessions": 3, "avg_events": max(10, avg_events + 1),
         "browse_rate": 0.15, "product_view_rate": 0.50, "cart_rate": 0.25, "checkout_rate": 0.10},
        
        # Power Buyers: High conversion (10%)
        {"name": "power_buyer", "weight": 0.10, "extra_sessions": 4, "avg_events": max(12, avg_events + 3),
         "browse_rate": 0.10, "product_view_rate": 0.45, "cart_rate": 0.30, "checkout_rate": 0.15},
    ]
    
    for uid in user_ids:
        # Assign persona to user with weighted probability
        persona = random.choices(PERSONAS, weights=[p["weight"] for p in PERSONAS], k=1)[0]
        print(f"User {str(uid)[-6:]}: {persona['name']}")

        for d in range(days):
            base_day = now - timedelta(days=d)
            # Vary sessions per day
            daily_sessions = sessions_per_user + persona["extra_sessions"] + random.randint(-1, 1)
            daily_sessions = max(1, daily_sessions)
            
            for s in range(daily_sessions):
                # More realistic hour distribution with peaks
                hour_weights = [
                    (0, 0.01), (1, 0.005), (2, 0.005), (3, 0.005), (4, 0.005), (5, 0.01),
                    (6, 0.02), (7, 0.04), (8, 0.06), (9, 0.08), (10, 0.09), (11, 0.08),
                    (12, 0.07), (13, 0.06), (14, 0.07), (15, 0.08), (16, 0.07), (17, 0.06),
                    (18, 0.05), (19, 0.08), (20, 0.09), (21, 0.07), (22, 0.04), (23, 0.02)
                ]
                hour = random.choices([h for h, w in hour_weights], weights=[w for h, w in hour_weights], k=1)[0]
                minute = random.randint(0,59)
                second = random.randint(0,59)
                dt = base_day.replace(hour=hour, minute=minute, second=second, microsecond=0)
                start_ts = int(dt.timestamp())
                generate_session_for_user(uid, start_ts, persona["avg_events"], products, persona)
                total_est += persona["avg_events"]
    return total_est

def seed_session_for_user(user_id: ObjectId, start_ts: int) -> str:
    """Create a browsing session (no events) consistent with runtime behavior.
    - Primary key: sessions._id == session_id
    - Foreign key: events.session_id references this id (when events are later emitted)
    Returns the created or existing session_id.
    """
    sid = str(ObjectId())
    ensure_browsing_session(sid, user_id, start_ts)
    return sid


def seed_sessions_for_users(user_ids: List[ObjectId], days: int, sessions_per_user: int) -> int:
    """Create session documents (no events) for a set of users across a time window.
    Mirrors the timing pattern used by event seeding.
    Returns the number of sessions created/upserted.
    """
    now = datetime.now(pytz.UTC)
    created = 0
    for uid in user_ids:
        for d in range(days):
            base_day = now - timedelta(days=d)
            for s in range(sessions_per_user):
                hour = random.choice([8,9,10,11,13,14,15,19,20,21])
                minute = random.randint(0,59)
                second = random.randint(0,59)
                dt = base_day.replace(hour=hour, minute=minute, second=second, microsecond=0)
                start_ts = int(dt.timestamp())
                sid = seed_session_for_user(uid, start_ts)
                # Verify existence immediately to count accurately
                try:
                    if sessions_col().find_one({"_id": sid}):
                        created += 1
                except Exception as e:
                    print(f"[seed] verification error for {sid}: {e}")
    return created


def seed_recent_events(user_ids: List[ObjectId], minutes: int, total_sessions: int, avg_events: int, seed_products_first: bool) -> int:
    """
    Seed events in the last N minutes - perfect for real-time dashboard testing.
    Spreads sessions evenly across the timeframe for realistic minute-by-minute data.
    """
    now = datetime.now(pytz.UTC)
    product_count = ensure_products(seed_products_first)
    if product_count == 0:
        print("⚠️  No products found. Run with --seed-products or seed_products.py first.")
        return 0
    
    products = list(products_col().find({}, {"_id": 1, "name": 1, "slug": 1, "category": 1, "price": 1}))
    
    PERSONAS = [
        # Bouncers: Quick exits (5%) - matches real-world bounce rates
        {"name": "bouncer", "weight": 0.05, "avg_events": 1, "extra_sessions": -2,
         "browse_rate": 1.0, "product_view_rate": 0.0, "cart_rate": 0.0, "checkout_rate": 0.0,
         "session_gap_min": 12, "session_gap_max": 72,  # Hours between sessions
         "event_time_min": 5, "event_time_max": 30},    # Seconds between events
        
        # Casual Browsers: Brief product views (30%)
        {"name": "casual_browser", "weight": 0.30, "avg_events": 4, "extra_sessions": -1,
         "browse_rate": 0.40, "product_view_rate": 0.50, "cart_rate": 0.08, "checkout_rate": 0.02,
         "session_gap_min": 8, "session_gap_max": 48,
         "event_time_min": 10, "event_time_max": 60},
        
        # Comparison Shoppers: Multiple product views, rare purchases (25%)
        {"name": "comparison_shopper", "weight": 0.25, "avg_events": 8, "extra_sessions": 1,
         "browse_rate": 0.20, "product_view_rate": 0.65, "cart_rate": 0.12, "checkout_rate": 0.03,
         "session_gap_min": 4, "session_gap_max": 24,
         "event_time_min": 20, "event_time_max": 180},
        
        # Regular Customers: Balanced browsing and buying (20%)
        {"name": "regular_customer", "weight": 0.20, "avg_events": 12, "extra_sessions": 2,
         "browse_rate": 0.25, "product_view_rate": 0.45, "cart_rate": 0.20, "checkout_rate": 0.10,
         "session_gap_min": 2, "session_gap_max": 36,
         "event_time_min": 15, "event_time_max": 120},
        
        # Loyal Shoppers: High engagement and conversion (15%)
        {"name": "loyal_shopper", "weight": 0.15, "avg_events": 15, "extra_sessions": 3,
         "browse_rate": 0.15, "product_view_rate": 0.40, "cart_rate": 0.30, "checkout_rate": 0.15,
         "session_gap_min": 1, "session_gap_max": 24,
         "event_time_min": 30, "event_time_max": 240},
        
        # Power Users: Very high engagement (5%)
        {"name": "power_user", "weight": 0.05, "avg_events": 20, "extra_sessions": 4,
         "browse_rate": 0.10, "product_view_rate": 0.35, "cart_rate": 0.35, "checkout_rate": 0.20,
         "session_gap_min": 0.5, "session_gap_max": 12,
         "event_time_min": 45, "event_time_max": 300},
    ]
    
    total_est = 0
    print(f"📊 Generating {total_sessions} sessions in last {minutes} minutes...")
    
    # Spread sessions evenly across the timeframe
    for i in range(total_sessions):
        # Random user
        uid = random.choice(user_ids)
        persona = random.choices(PERSONAS, weights=[p["weight"] for p in PERSONAS], k=1)[0]
        
        # Calculate timestamp - spread evenly with some randomness
        minutes_ago = (i / total_sessions) * minutes
        jitter = random.uniform(-minutes / (total_sessions * 2), minutes / (total_sessions * 2))
        minutes_ago = max(0, min(minutes, minutes_ago + jitter))
        
        session_time = now - timedelta(minutes=minutes_ago)
        start_ts = int(session_time.timestamp())
        
        # Generate session
        events_count = persona["avg_events"]
        if i % 10 == 0:  # Progress indicator
            print(f"  Session {i+1}/{total_sessions}: {persona['name']} @ {session_time.strftime('%H:%M:%S')}")
        
        generate_session_for_user(uid, start_ts, events_count, products, persona)
        total_est += events_count
    
    return total_est


def main():
    parser = argparse.ArgumentParser(description="Seed realistic customer-like data")
    parser.add_argument("--username", type=str, default=None, help="Seed only for this username (create if missing)")
    parser.add_argument("--user-count", type=int, default=100, help="Number of users when --username not provided")
    parser.add_argument("--days", type=int, default=10, help="Days back to generate")
    parser.add_argument("--sessions-per-user", type=int, default=random.randint(3, 10), help="Sessions per user per day")
    parser.add_argument("--avg-events", type=int, default=random.randint(5, 50), help="Average events per session")
    parser.add_argument("--seed-products", action="store_true", help="Seed products first if empty")
    parser.add_argument("--recent-minutes", type=int, default=None, help="Generate data in last N minutes (overrides --days)")
    parser.add_argument("--recent-sessions", type=int, default=50, help="Number of sessions when using --recent-minutes")

    args = parser.parse_args()

    if args.username:
        user_ids = ensure_users(args.username, 1)
    else:
        user_ids = ensure_users(None, args.user_count)

    # Recent mode - for real-time dashboard testing
    if args.recent_minutes is not None:
        print(f"🚀 RECENT MODE: Seeding {args.recent_sessions} sessions in last {args.recent_minutes} minutes")
        est = seed_recent_events(user_ids, args.recent_minutes, args.recent_sessions, args.avg_events, args.seed_products)
        print(f"✅ Estimated events inserted: ~{est}")
        print(f"💡 Refresh your dashboard to see live data!")
        return

    # Normal mode - historical data
    print(f"Seeding realistic data for {len(user_ids)} users...")
    est = seed_event_for_users(user_ids, args.days, args.sessions_per_user, args.avg_events, args.seed_products)
    sessions_created = seed_sessions_for_users(user_ids, args.days, args.sessions_per_user)
    print(f"✅ Estimated events inserted: ~{est}")
    print(f"✅ Sessions upserted: {sessions_created}")

if __name__ == "__main__":
    main()
