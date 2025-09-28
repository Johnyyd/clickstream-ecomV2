import requests
import os
import time

BASE = "https://openrouter.ai/api/v1/keys"

def _headers():
    key = os.getenv("OPENROUTER_PROVISIONING_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_PROVISIONING_KEY is not set in environment")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

def create_runtime_key(name="runtime-key-auto", limit=None):
    payload = {"name": name}
    if limit is not None:
        payload["limit"] = float(limit)
    resp = requests.post(BASE, json=payload, headers=_headers(), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # response contains "key" (the secret) and "data" metadata
    return data["key"], data["data"]

def list_keys():
    resp = requests.get(BASE, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()

def disable_key(key_hash):
    # depends on API: usually there's PATCH/DELETE; adjust per docs
    url = f"{BASE}/{key_hash}"
    resp = requests.patch(url, json={"disabled": True}, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()

# Example usage:
if __name__ == "__main__":
    new_key, meta = create_runtime_key(name=f"svc-runtime-{int(time.time())}", limit=100.0)
    print("NEW KEY (store it securely):", new_key)
    print("META:", meta)
