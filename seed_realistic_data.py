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

from db import users_col, products_col, sessions_col
from ingest import ingest_event
from auth import create_user

PAGES = ["/home", "/category", "/search", "/product", "/cart", "/checkout"]


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
            uid = create_user(target_username, email, pw)
            try:
                # Normalize to ObjectId and ensure role is 'user'
                from bson import ObjectId as _OID
                users_col().update_one({"_id": _OID(uid)}, {"$set": {"role": "user"}})
                u = users_col().find_one({"_id": _OID(uid)})
            except Exception:
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
            uid = create_user(uname, f"{uname}@example.com", f"{uname}123")
            from bson import ObjectId as _OID
            users_col().update_one({"_id": _OID(uid)}, {"$set": {"role": "user"}})
            pool.append(_OID(uid))
        except Exception:
            u = users_col().find_one({"username": uname})
            if u:
                pool.append(u["_id"])  # type: ignore[index]
    return pool[:count]


def emit_event(user_id, session_id, ts, page, event_type, props=None, client_id: Optional[str]=None):
    ev = {
        "user_id": user_id,  # keep as ObjectId
        "client_id": client_id or "",
        "session_id": session_id,
        "timestamp": int(ts),  # epoch seconds as ingest_event supports
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


def ensure_browsing_session(session_id: str, user_id: ObjectId, start_ts: int, client_id: Optional[str] = None) -> bool:
    """Upsert a browsing session document using _id == session_id to mirror runtime behavior.
    Returns True if the upsert was acknowledged, False otherwise.
    """
    try:
        ts = datetime.fromtimestamp(start_ts, tz=pytz.UTC)
        res = sessions_col().update_one(
            {"_id": session_id},
            {
                "$setOnInsert": {
                    "_id": session_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "client_id": client_id,
                    "created_at": ts,
                    "pages": [],
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


def generate_session_for_user(user_id: ObjectId, start_ts: int, avg_events: int, products: list[dict]):
    """Generate a realistic session with plausible navigation and conversion behavior."""
    sid = f"session_{str(user_id)[-6:]}_{start_ts}"
    current_ts = start_ts
    # Deterministic client id per user (stable across sessions); adjust if you want per-session IDs
    client_id = f"client_{str(user_id)[-6:]}"

    # First event: home
    ensure_browsing_session(sid, user_id, current_ts, client_id)
    emit_event(user_id, sid, current_ts, "/home", "pageview", {"referrer": random.choice(["direct","email","social","ads"]) }, client_id)

    viewed_product_ids: list[str] = []
    cart = []

    # Events count ~ N(avg, 2)
    n_events = max(3, random.randint(avg_events - 2, avg_events + 2))

    for i in range(1, n_events):
        # spacing 15s..4m
        current_ts += random.randint(15, 240)
        r = random.random()

        if r < 0.35:  # category/search discoverability
            if random.random() < 0.55:
                category = random.choice([p.get("category") for p in products])
                emit_event(user_id, sid, current_ts, "/category", "pageview", {"category": category}, client_id)
            else:
                term = random.choice(["laptop","phone","coffee","shoes","shirt","pizza","sushi"]) 
                emit_event(user_id, sid, current_ts, "/search", "search", {"search_term": term}, client_id)
        elif r < 0.70:  # view product
            p = realistic_product(products)
            viewed_product_ids.append(str(p["_id"]))
            emit_event(
                user_id,
                sid,
                current_ts,
                f"/product/{p['_id']}",
                "pageview",
                {
                    "product_id": str(p["_id"]),
                    "product_name": p["name"],
                    "product_category": p["category"],
                    "product_price": p["price"],
                },
                client_id,
            )
        elif r < 0.88:  # add to cart
            if viewed_product_ids:
                prod_id = random.choice(viewed_product_ids)
                p = next((pp for pp in products if str(pp["_id"]) == prod_id), None)
                if p:
                    cart.append(p)
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
                        client_id,
                    )
            else:
                emit_event(user_id, sid, current_ts, "/home", "pageview", None, client_id)
        else:  # checkout / purchase
            if cart and random.random() < 0.65:
                total = sum(item["price"] for item in cart)
                emit_event(
                    user_id,
                    sid,
                    current_ts,
                    "/checkout",
                    "purchase",
                    {
                        "cart_items": len(cart),
                        "total_amount": round(total, 2),
                        "payment_method": random.choice(["credit_card","paypal","apple_pay"]),
                        "order_id": f"order_{random.randint(1000,9999)}",
                    },
                    client_id,
                )
                cart.clear()
            else:
                emit_event(user_id, sid, current_ts, random.choice(["/home","/category","/search"]), "pageview", None, client_id)


def seed_event_for_users(user_ids: List[ObjectId], days: int, sessions_per_user: int, avg_events: int, seed_products_first: bool):
    product_count = ensure_products(seed_products_first)
    if product_count == 0:
        print("No products found. Please seed products first.")
        return 0
    products = list(products_col().find({}))

    now = datetime.now(pytz.UTC) # error
    total_est = 0
    for uid in user_ids:
        # Define user persona for conversion/engagement variety
        persona = random.choice([
            {"name": "browser", "extra_sessions": 0, "avg_events": avg_events - 1},
            {"name": "shopper", "extra_sessions": 2, "avg_events": avg_events},
            {"name": "buyer", "extra_sessions": 1, "avg_events": avg_events + 1},
            {"name": "returning", "extra_sessions": 3, "avg_events": avg_events},
        ])

        for d in range(days):
            base_day = now - timedelta(days=d)
            for s in range(sessions_per_user + persona["extra_sessions"]):
                hour = random.choice([8,9,10,11,13,14,15,19,20,21])
                minute = random.randint(0,59)
                second = random.randint(0,59)
                dt = base_day.replace(hour=hour, minute=minute, second=second, microsecond=0)
                start_ts = int(dt.timestamp())
                generate_session_for_user(uid, start_ts, persona["avg_events"], products)
                total_est += persona["avg_events"]
    return total_est

def seed_session_for_user(user_id: ObjectId, start_ts: int, client_id: Optional[str] = None) -> str:
    """Create a browsing session (no events) consistent with runtime behavior.
    - Primary key: sessions._id == session_id
    - Foreign key: events.session_id references this id (when events are later emitted)
    Returns the created or existing session_id.
    """
    sid = f"session_{str(user_id)[-6:]}_{start_ts}"
    ensure_browsing_session(sid, user_id, start_ts, client_id)
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


def main():
    parser = argparse.ArgumentParser(description="Seed realistic customer-like data")
    parser.add_argument("--username", type=str, default=None, help="Seed only for this username (create if missing)")
    parser.add_argument("--user-count", type=int, default=100, help="Number of users when --username not provided")
    parser.add_argument("--days", type=int, default=7, help="Days back to generate")
    parser.add_argument("--sessions-per-user", type=int, default=5, help="Sessions per user per day")
    parser.add_argument("--avg-events", type=int, default=7, help="Average events per session")
    parser.add_argument("--seed-products", action="store_true", help="Seed products first if empty")

    args = parser.parse_args()

    if args.username:
        user_ids = ensure_users(args.username, 1)
    else:
        user_ids = ensure_users(None, args.user_count)

    print(f"Seeding realistic data for {len(user_ids)} users...")
    est = seed_event_for_users(user_ids, args.days, args.sessions_per_user, args.avg_events, args.seed_products)
    sessions_created = seed_sessions_for_users(user_ids, args.days, args.sessions_per_user)
    print(f"✅ Estimated events inserted: ~{est}")
    print(f"✅ Sessions upserted: {sessions_created}")

if __name__ == "__main__":
    main()
