# openrouter_client.py
import os
import requests
import json

OPENROUTER_ENDPOINT = os.environ.get("OPENROUTER_ENDPOINT", "https://api.openrouter.ai/v1/chat/completions")
# The endpoint above is a placeholder — thay bằng endpoint chính xác bạn dùng nếu cần.

def call_openrouter(api_key, prompt, model="gpt-4o-mini", max_tokens=500):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful analytics assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2
    }
    resp = requests.post(OPENROUTER_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=30)
    resp.raise_for_status()
    return resp.json()
