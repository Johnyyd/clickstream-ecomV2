# seed_demo_data.py
# Generate richer demo data into MongoDB leveraging existing DB structure.
# - Seeds products (re-uses simulate_clickstream.seed_products)
# - Creates or reuses users
# - Generates sessions per user across multiple days with realistic behavior
# - Inserts events via ingest_event() to ensure consistent schema

import argparse
import random
import time
from datetime import datetime, timedelta
from typing import List, Optional

from bson import ObjectId

from db import users_col, products_col, get_db
from ingest import ingest_event
from simulate_clickstream import seed_products, PRODUCTS
from auth import create_user


PAGES = [
    "/home",
    "/category",
    "/search",
    "/product",
    "/cart",
    "/checkout",
]


def ensure_products() -> int:
    seed_products()
    return products_col().count_documents({})


DEFAULT_USERNAMES = [
    ("alice", "alice@example.com", "alice123"),
    ("bob", "bob@example.com", "bob123"),
    ("charlie", "charlie@example.com", "charlie123"),
    ("diana", "diana@example.com", "diana123"),
    ("eve", "eve@example.com", "eve123"),
]


def ensure_users(target_username: Optional[str], count: int) -> List[ObjectId]:
    ids: List[ObjectId] = []
    if target_username:
        u = users_col().find_one({"username": target_username})
        if not u:
            email = f"{target_username}@example.com"
            pw = f"{target_username}123"
            uid = create_user(target_username, email, pw)
            u = users_col().find_one({"_id": uid})
        ids.append(u["_id"])  # type: ignore[index]
        return ids

    # Create/reuse N default users
    existing = list(users_col().find({}))
    existing_by_username = {u["username"]: u for u in existing}

    # Use DEFAULT_USERNAMES first then synthesize more if needed
    pool = []
    for uname, email, pw in DEFAULT_USERNAMES:
        if uname in existing_by_username:
            pool.append(existing_by_username[uname]["_id"])  # type: ignore[index]
        else:
            try:
                uid = create_user(uname, email, pw)
                pool.append(uid)
            except Exception:
                # Race or exists
                u = users_col().find_one({"username": uname})
                if u:
                    pool.append(u["_id"])  # type: ignore[index]

    # Top up to requested count with synthetic users
    idx = 1
    while len(pool) < count:
        uname = f"user{idx:03d}"
        idx += 1
        if users_col().find_one({"username": uname}):
            continue
        uid = create_user(uname, f"{uname}@example.com", "password123")
        pool.append(uid)

    return pool[:count]


def random_product():
    return random.choice(PRODUCTS)


def emit_event(user_id, session_id, ts, page, event_type, props=None):
    ev = {
        "user_id": user_id,  # keep as ObjectId
        "session_id": session_id,
        "timestamp": int(ts),  # epoch seconds as ingest_event supports
        "page": page,
        "event_type": event_type,
        "properties": props or {},
    }
    ingest_event(ev)


def generate_session_for_user(user_id: ObjectId, start_ts: int, avg_events: int):
    # Create a session id based on user id and timestamp for realism
    sid = f"session_{str(user_id)[-6:]}_{start_ts}"

    # First event: home
    emit_event(user_id, sid, start_ts, "/home", "pageview", {"referrer": random.choice(["direct","email","social","ads"])})

    current_ts = start_ts
    viewed_product_ids = []
    cart = []

    # Number of events: avg +/- 2, min 3
    n_events = max(3, random.randint(avg_events - 2, avg_events + 2))

    for i in range(1, n_events):
        # space events 10s..5m
        current_ts += random.randint(10, 300)

        r = random.random()
        if r < 0.35:  # browse category or search
            if random.random() < 0.5:
                category = random.choice([p["category"] for p in PRODUCTS])
                emit_event(user_id, sid, current_ts, "/category", "pageview", {"category": category})
            else:
                term = random.choice(["laptop","phone","coffee","shoes","shirt","pizza","sushi"]) 
                emit_event(user_id, sid, current_ts, "/search", "search", {"search_term": term})
        elif r < 0.65:  # view product
            p = random_product()
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
            )
        elif r < 0.85:  # add to cart
            if viewed_product_ids:
                prod_id = random.choice(viewed_product_ids)
                p = next((pp for pp in PRODUCTS if str(pp["_id"]) == prod_id), None)
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
                    )
            else:
                emit_event(user_id, sid, current_ts, "/home", "pageview")
        else:  # checkout/purchase 15%
            if cart and random.random() < 0.7:
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
                )
                cart.clear()
            else:
                emit_event(user_id, sid, current_ts, random.choice(["/home","/category","/search"]), "pageview")


def seed_for_users(user_ids: List[ObjectId], days: int, sessions_per_user: int, avg_events: int):
    now = datetime.utcnow()
    total_events = 0
    for uid in user_ids:
        for d in range(days):
            # Distribute sessions across hours within the day
            base_day = now - timedelta(days=d)
            for s in range(sessions_per_user):
                hour = random.choice([8,9,10,11,13,14,15,19,20,21])
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                dt = base_day.replace(hour=hour, minute=minute, second=second, microsecond=0)
                start_ts = int(dt.timestamp())
                before = products_col().count_documents({})
                generate_session_for_user(uid, start_ts, avg_events)
                # Approximate count increase (not exact without querying each insert)
                total_events += avg_events
    return total_events


def main():
    parser = argparse.ArgumentParser(description="Seed richer demo data for analysis")
    parser.add_argument("--username", type=str, default=None, help="Seed only for this username (create if missing)")
    parser.add_argument("--user-count", type=int, default=5, help="Number of users to seed if --username not provided")
    parser.add_argument("--days", type=int, default=7, help="Number of days back to generate sessions for")
    parser.add_argument("--sessions-per-user", type=int, default=10, help="Number of sessions per user per day")
    parser.add_argument("--avg-events", type=int, default=8, help="Average events per session")

    args = parser.parse_args()

    print("Seeding products...")
    product_total = ensure_products()
    print(f" -> Products available: {product_total}")

    print("Ensuring users...")
    uids = ensure_users(args.username, args.user_count)
    print(f" -> Users targeted: {len(uids)}")

    print(
        f"Generating data for days={args.days}, sessions_per_user={args.sessions_per_user}, avg_events={args.avg_events}"
    )
    total_events_est = seed_for_users(uids, args.days, args.sessions_per_user, args.avg_events)

    print("\n✅ Seeding complete.")
    print(f"Estimated events inserted: ~{total_events_est}")
    print("You can now login as one of these users and run /api/analyze to see user-scoped insights.")


if __name__ == "__main__":
    main()
