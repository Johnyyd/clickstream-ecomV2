# openrouter_client.py
import os
import requests
import json

# Endpoint configuration: prefer env override; otherwise try official then legacy
OPENROUTER_ENV_ENDPOINT = os.environ.get("OPENROUTER_ENDPOINT")
OPENROUTER_DEFAULT_ENDPOINTS = [
    "https://openrouter.ai/api/v1/chat/completions",   # official
    "https://api.openrouter.ai/v1/chat/completions",   # legacy
]
# The endpoint above is a placeholder — thay bằng endpoint chính xác bạn dùng nếu cần.

def _build_messages(prompt: str) -> list:
    """Build messages that enforce STRICT JSON output with actionable insights."""
    schema_instructions = (
        "Return ONLY valid JSON with the following schema and nothing else. "
        "Do not include backticks. Do not include prose outside JSON.\n\n"
        "Required keys: {\n"
        "  'executive_summary': str,\n"
        "  'key_insights': [str],\n"
        "  'recommendations': [str],\n"
        "  'decisions': [str],\n"
        "  'next_best_actions': [str],\n"
        "  'risk_alerts': [str],\n"
        "  'kpis': {\n"
        "    'total_events': number,\n"
        "    'total_sessions': number,\n"
        "    'bounce_rate': number,\n"
        "    'avg_session_duration_seconds': number\n"
        "  }\n"
        "}"
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a senior product analytics copilot. "
                "Your job: read structured clickstream metrics and output clear, actionable business guidance. "
                "Always be concise and decisive."
            ),
        },
        {
            "role": "user",
            "content": f"{schema_instructions}\n\nHere are the analysis inputs to consider (JSON-like):\n{prompt}",
        },
    ]


def _safe_json_parse(text: str):
    """Try to parse strict JSON from model content. Attempts minor cleanup if needed."""
    try:
        return json.loads(text)
    except Exception:
        # Try to extract JSON substring between first { and last }
        if "{" in text and "}" in text:
            try:
                start = text.index("{")
                end = text.rindex("}") + 1
                return json.loads(text[start:end])
            except Exception:
                pass
        return None


def call_openrouter(api_key: str, prompt: str, model: str = "x-ai/grok-4-fast:free", max_tokens: int = 900, temperature: float = 0.2, retries: int = 2, timeout: int = 45):
    """
    Call OpenRouter to transform analysis metrics into structured, actionable JSON.

    Returns a dict with keys:
    - status: "ok" | "error"
    - parsed: dict | None  (structured insights if parsing succeeded)
    - raw: dict | None     (raw provider JSON)
    - error: str | None
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Recommended headers per OpenRouter docs (optional but helpful)
        "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER", "http://localhost:8000"),
        "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "Clickstream Ecom Dashboard"),
    }

    payload = {
        "model": model,
        "messages": _build_messages(prompt),
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    last_err = None
    # Build list of endpoints to try (env first, then defaults), de-duplicated
    endpoints_raw = ([OPENROUTER_ENV_ENDPOINT] if OPENROUTER_ENV_ENDPOINT else []) + OPENROUTER_DEFAULT_ENDPOINTS
    seen = set()
    endpoints = []
    for ep in endpoints_raw:
        if ep and ep not in seen:
            endpoints.append(ep)
            seen.add(ep)

    for endpoint in endpoints:
        for attempt in range(retries + 1):
            try:
                # Diagnostic logging for troubleshooting endpoint/model issues
                try:
                    print(f"[OpenRouter] Endpoint={endpoint} Model={model} MaxTokens={max_tokens} Temp={temperature}")
                except Exception:
                    pass
                resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=timeout)
                resp.raise_for_status()
                raw = resp.json()

                # Try to extract content
                content = None
                try:
                    content = raw["choices"][0]["message"]["content"]
                except Exception:
                    # Some providers may return different structure; fallback to entire raw
                    content = json.dumps(raw)

                parsed = _safe_json_parse(content)
                return {"status": "ok", "parsed": parsed, "raw": raw, "error": None}
            except Exception as e:
                last_err = f"endpoint={endpoint} error={e}"
                if attempt < retries:
                    continue
                # move on to next endpoint after exhausting retries
                break
    return {"status": "error", "parsed": None, "raw": None, "error": last_err}
