# e2e_user_scope_test.py
# End-to-end smoke test for user-scoped analysis flow

import json
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"


def post(path, body, headers=None):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url=f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.getcode(), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = e.read().decode("utf-8")
            return e.code, json.loads(payload)
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def get(path, headers=None):
    req = urllib.request.Request(
        url=f"{BASE}{path}",
        headers={**(headers or {})},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.getcode(), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = e.read().decode("utf-8")
            return e.code, json.loads(payload)
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def main():
    username = "alice"
    email = "alice@example.com"
    password = "alice123"

    print("1) Signup (ignore if already exists)...")
    code, resp = post("/api/signup", {"username": username, "email": email, "password": password})
    print("   ->", code, resp)

    print("2) Login...")
    code, resp = post("/api/login", {"username": username, "password": password})
    if code != 200 or "token" not in resp:
        raise SystemExit(f"Login failed: {code} {resp}")
    token = resp["token"]
    auth = {"Authorization": token}
    print("   -> token acquired")

    print("3) Ingest 3 events (Authorization header attaches user_id)...")
    events = [
        {"client_id": "c1", "page": "/home", "event_type": "pageview"},
        {"client_id": "c1", "page": "/product", "event_type": "pageview"},
        {"client_id": "c1", "page": "/checkout", "event_type": "pageview"},
    ]
    for i, ev in enumerate(events, 1):
        code, resp = post("/api/ingest", ev, headers=auth)
        print(f"   -> event {i}:", code, resp)
        if code not in (200, 201):
            raise SystemExit(f"Ingest failed: {code} {resp}")

    print("4) Trigger analysis for this user...")
    code, resp = post("/api/analyze", {"params": {"limit": 100}}, headers=auth)
    print("   ->", code, resp)
    if code != 200:
        raise SystemExit(f"Analyze failed: {code} {resp}")

    print("5) Fetch analyses list for this user...")
    # Small wait to ensure DB write visible
    time.sleep(0.5)
    code, resp = get("/api/analyses", headers=auth)
    print("   ->", code)
    print(json.dumps(resp, indent=2))

    if isinstance(resp, list) and resp:
        print("6) Fetch latest analysis by ID...")
        latest_id = resp[0].get("_id")
        code, detail = get(f"/api/analyses/{latest_id}", headers=auth)
        print("   ->", code)
        print(json.dumps(detail, indent=2))

    print("\nE2E user-scoped analysis test completed.")


if __name__ == "__main__":
    main()
