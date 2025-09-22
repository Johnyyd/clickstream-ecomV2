"""
backfill_sessions.py

Populate the sessions collection from existing events. Safe to run multiple times (idempotent upserts).

Usage (PowerShell):
  venv/Scripts/python.exe backfill_sessions.py --since-days 14
  venv/Scripts/python.exe backfill_sessions.py  # all events (may be slow on very large datasets)
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Any, Dict

from bson import ObjectId

from db import events_col, sessions_col


def upsert_session(session_id: str, user_id: Any, client_id: str | None, ts) -> None:
    sessions_col().update_one(
        {"session_id": session_id},
        {
            "$setOnInsert": {
                "session_id": session_id,
                "user_id": user_id,
                "client_id": client_id,
                "created_at": ts,
                "first_event_at": ts,
                "pages": [],
            },
            "$max": {"last_event_at": ts},
            "$min": {"first_event_at": ts},
            "$inc": {"event_count": 1},
        },
        upsert=True,
    )


def main():
    ap = argparse.ArgumentParser(description="Backfill sessions from events")
    ap.add_argument("--since-days", type=int, default=None, help="Only backfill for recent days")
    ap.add_argument("--limit", type=int, default=None, help="Limit number of events processed")

    args = ap.parse_args()

    q: Dict[str, Any] = {}
    if args.since_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=args.since_days)
        q["$or"] = [
            {"timestamp": {"$gte": int(cutoff.timestamp())}},
            {"timestamp": {"$gte": cutoff}},
        ]

    projection = {
        "_id": 1,
        "session_id": 1,
        "user_id": 1,
        "client_id": 1,
        "timestamp": 1,
    }

    cur = events_col().find(q, projection).sort("timestamp", 1)
    if args.limit:
        cur = cur.limit(args.limit)

    count = 0
    for ev in cur:
        sid = ev.get("session_id")
        if not sid:
            continue
        ts = ev.get("timestamp")
        upsert_session(sid, ev.get("user_id"), ev.get("client_id"), ts)
        count += 1
        if count % 10000 == 0:
            print(f"Processed {count} events...")

    print(f"Done. Backfilled from {count} events.")


if __name__ == "__main__":
    main()
