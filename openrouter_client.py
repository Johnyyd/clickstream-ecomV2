# openrouter_client.py
import os
import requests
import json

# Endpoint configuration: prefer env override; otherwise use official endpoint
OPENROUTER_ENV_ENDPOINT = os.environ.get("OPENROUTER_ENDPOINT")
OPENROUTER_DEFAULT_ENDPOINTS = [
    "https://openrouter.ai/api/v1/chat/completions",   # official endpoint
]

def _build_messages(prompt: str) -> list:
    """Build messages that enforce STRICT JSON output with actionable insights."""
    schema_instructions = (
        "Return ONLY valid JSON with the following schema and nothing else. "
        "Do not include backticks, markdown formatting, or any text outside the JSON object.\n\n"
        "REQUIRED JSON SCHEMA:\n"
        "{\n"
        "  'executive_summary': string (2-3 câu tóm tắt tổng quan về hiệu suất website),\n"
        "  'key_insights': array of strings (5-7 insights quan trọng nhất từ dữ liệu Spark analysis),\n"
        "  'recommendations': array of strings (5-7 khuyến nghị cụ thể để cải thiện business),\n"
        "  'decisions': array of strings (3-5 quyết định chiến lược nên thực hiện ngay),\n"
        "  'next_best_actions': array of strings (5-7 hành động cụ thể cần làm trong 7 ngày tới),\n"
        "  'risk_alerts': array of strings (các cảnh báo về rủi ro hoặc vấn đề cần chú ý),\n"
        "  'recommendations_for_user': array of strings (3-5 khuyến nghị cho end-user dựa trên behavior),\n"
        "  'recommendations_for_user_products': array of objects [\n"
        "    {\n"
        "      'product_id': string (ID từ product catalog),\n"
        "      'name': string (tên sản phẩm),\n"
        "      'reason': string (lý do recommend dựa trên clickstream data)\n"
        "    }\n"
        "  ] (3-5 sản phẩm được recommend),\n"
        "  'kpis': {\n"
        "    'total_events': number,\n"
        "    'total_sessions': number,\n"
        "    'bounce_rate': number (0-1),\n"
        "    'avg_session_duration_seconds': number\n"
        "  },\n"
        "  'traffic_insights': {\n"
        "    'peak_hours': array of strings (giờ cao điểm và phân tích),\n"
        "    'user_behavior_patterns': array of strings (các pattern hành vi user),\n"
        "    'popular_categories': array of strings (categories phổ biến và insights)\n"
        "  },\n"
        "  'conversion_analysis': {\n"
        "    'funnel_performance': array of strings (phân tích hiệu suất từng funnel),\n"
        "    'drop_off_points': array of strings (điểm user rời bỏ nhiều nhất),\n"
        "    'optimization_opportunities': array of strings (cơ hội tối ưu conversion)\n"
        "  }\n"
        "}\n\n"
        "IMPORTANT ANALYSIS GUIDELINES:\n"
        "- Phân tích KỸ LƯỠNG dữ liệu từ Spark Analysis (spark_summary, detailed_metrics)\n"
        "- Tập trung vào: conversion rates, funnel metrics, session behavior, time patterns\n"
        "- Đưa ra insights CỤ THỂ với SỐ LIỆU (ví dụ: 'Conversion rate từ home->checkout chỉ 8.6%')\n"
        "- Recommendations phải ACTIONABLE và có thể đo lường được\n"
        "- Product recommendations phải dựa trên: top viewed products, search terms, cart behavior\n"
        "- Risk alerts: identify vấn đề nghiêm trọng (low conversion, high bounce, funnel issues)\n"
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a SENIOR E-COMMERCE DATA ANALYST with expertise in:\n"
                "- Clickstream analysis and user behavior tracking\n"
                "- Conversion funnel optimization\n"
                "- Product recommendation systems\n"
                "- Business intelligence and KPI analysis\n\n"
                "Your task: Analyze Spark-generated clickstream data and provide DETAILED, ACTIONABLE insights.\n"
                "Be SPECIFIC with numbers, percentages, and concrete recommendations.\n"
                "Focus on BUSINESS IMPACT and ROI.\n"
                "Output MUST be valid JSON only - no markdown, no explanations outside JSON."
            ),
        },
        {
            "role": "user",
            "content": f"{schema_instructions}\n\n=== CLICKSTREAM DATA FROM SPARK ANALYSIS ===\n{prompt}",
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


def call_openrouter(api_key: str, prompt: str, model: str = "z-ai/glm-4.5-air:free", max_tokens: int = 900, temperature: float = 0.0, retries: int = 2, timeout: int = 45):
    """
    Call OpenRouter to transform analysis metrics into structured, actionable JSON.

    Returns a dict with keys:
    - status: "ok" | "error"
    - parsed: dict | None  (structured insights if parsing succeeded)
    - raw: dict | None     (raw provider JSON)
    - error: str | None
    """
    # Allow the model to be overridden by environment variable
    env_model = os.environ.get("OPENROUTER_MODEL")
    if env_model:
        model = env_model

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Recommended headers per OpenRouter docs (optional but helpful)
        "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER", "http://localhost:8000/dashboard"),
        "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "Clickstream Ecom Dashboard"),
    }

    payload = {
        "model": model,
        "messages": _build_messages(prompt),
        "max_tokens": max_tokens,
        "temperature": temperature,
        # Hint models to return strict JSON if supported by the provider
        "response_format": {"type": "json_object"},
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
