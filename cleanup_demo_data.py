"""
cleanup_demo_data.py

Safely identify and clean up noisy/bot-like demo data while preserving schema.
- Default: TAGS flagged events/sessions/users instead of deleting (non-destructive)
- Optional: --delete to actually delete flagged documents
- Optional: --since-days N to keep only recent data (flag older)
- Filters target known demo patterns and unrealistic traces

Usage (PowerShell):
  # Dry-run: report counts only
  venv/Scripts/python.exe cleanup_demo_data.py --dry-run

  # Tag noisy data (non-destructive)
  venv/Scripts/python.exe cleanup_demo_data.py

  # Tag + delete flagged
  venv/Scripts/python.exe cleanup_demo_data.py --delete

  # Only keep recent N days (flag older)
  venv/Scripts/python.exe cleanup_demo_data.py --since-days 14
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any

from bson import ObjectId
from pymongo import UpdateOne, DeleteMany

from db import events_col, sessions_col, users_col


KNOWN_DEMO_CLIENTS = [
    "client-demo",  # from dashboard.js sample ingest
]

KNOWN_DEMO_SOURCES = {
    "simulation",
    "basic_sim",
    "seed_demo",
    "realistic_seed",  # keep but allow filtering explicitly
}

KNOWN_TEST_PAGES_PREFIX = (
    "/product/",
    "/home",
    "/category",
    "/search",
    "/cart",
    "/checkout",
)


def is_string_id(val) -> bool:
    return isinstance(val, str) and not ObjectId.is_valid(val)


def find_flagged_events(since_days: int | None) -> Dict[str, Any]:
    q: Dict[str, Any] = {}
    if since_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=since_days)
        # events.timestamp may be epoch int or datetime; handle via $or
        q["$or"] = [
            {"timestamp": {"$gte": int(cutoff.timestamp())}},
            {"timestamp": {"$gte": cutoff}},
        ]
    # Base cursor (limit large scans by projection)
    cur = events_col().find(q, {
        "_id": 1,
        "user_id": 1,
        "session_id": 1,
        "timestamp": 1,
        "page": 1,
        "event_type": 1,
        "client_id": 1,
        "properties": 1,
        "flag": 1,
    })

    flagged_ids: List[ObjectId] = []
    reasons: Dict[str, int] = {}

    def add_reason(reason: str, _id: ObjectId):
        flagged_ids.append(_id)
        reasons[reason] = reasons.get(reason, 0) + 1

    for ev in cur:
        # Already flagged → skip
        if ev.get("flag", {}).get("noisy"):
            continue

        props = ev.get("properties") or {}
        # Heuristics
        if ev.get("client_id") in KNOWN_DEMO_CLIENTS:
            add_reason("demo_client", ev["_id"]) ; continue
        src = props.get("source")
        if src in KNOWN_DEMO_SOURCES:
            add_reason("known_source", ev["_id"]) ; continue
        if is_string_id(ev.get("user_id")):
            add_reason("string_user_id", ev["_id"]) ; continue
        page = (ev.get("page") or "").strip()
        if not page or not page.startswith("/"):
            add_reason("invalid_page", ev["_id"]) ; continue
        # Unrealistic: event_type missing
        if not ev.get("event_type"):
            add_reason("missing_event_type", ev["_id"]) ; continue

    return {"ids": flagged_ids, "reasons": reasons}


def tag_or_delete_events(flagged: List[ObjectId], delete: bool) -> Dict[str, int]:
    if not flagged:
        return {"updated": 0, "deleted": 0}
    if delete:
        res = events_col().delete_many({"_id": {"$in": flagged}})
        return {"updated": 0, "deleted": res.deleted_count}
    # tag
    ops = [
        UpdateOne({"_id": _id}, {"$set": {"flag.noisy": True, "flag.updated_at": datetime.utcnow()}})
        for _id in flagged
    ]
    if ops:
        r = events_col().bulk_write(ops, ordered=False)
        return {"updated": r.modified_count, "deleted": 0}
    return {"updated": 0, "deleted": 0}


def main():
    ap = argparse.ArgumentParser(description="Cleanup noisy/demo data while preserving schema")
    ap.add_argument("--dry-run", action="store_true", help="Only show stats, do not modify")
    ap.add_argument("--delete", action="store_true", help="Delete flagged events instead of tagging")
    ap.add_argument("--since-days", type=int, default=None, help="Only consider recent events (days)")

    args = ap.parse_args()

    flagged = find_flagged_events(args.since_days)
    print("Flag reasons:")
    for k, v in sorted(flagged["reasons"].items(), key=lambda x: -x[1]):
        print(f" - {k}: {v}")
    print(f"Total flagged events: {len(flagged['ids'])}")

    if args.dry_run:
        print("Dry-run. No changes applied.")
        return

    res = tag_or_delete_events(flagged["ids"], args.delete)
    print(f"Updated (tagged): {res['updated']}")
    print(f"Deleted: {res['deleted']}")


if __name__ == "__main__":
    main()
