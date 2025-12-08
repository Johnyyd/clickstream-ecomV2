# meta-llama/llama-3.2-3b-instruct:free
async def chat(api_key: str, prompt: str) -> Dict:

    try:
        base_url = (
            getattr(settings, "OPENROUTER_API_URL", None)
            or "https://openrouter.ai/api/v1"
        )

        raw_key = api_key
        if not raw_key:
            s_key = getattr(settings, "OPENROUTER_API_KEY", None)
            if s_key is not None and not isinstance(s_key, str):
                try:
                    s_key = s_key.get_secret_value()
                except Exception:
                    pass
            raw_key = s_key

        key = raw_key

        logger = logging.getLogger(__name__)

        if base_url and key:
            try:
                import json as _json

                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        f"{base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "Clickstream Dashboard",
                        },
                        json={
                            "model": "meta-llama/llama-3.2-3b-instruct:free",
                            "messages": [
                                {"role": "system", "content": prompt},
                                {
                                    "role": "user",
                                    "content": _json.dumps(
                                        prompt or {}, ensure_ascii=False
                                    ),
                                },
                            ],
                            "response_format": {"type": "json_object"},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    content = None
                    try:
                        choices = data.get("choices") or []
                        if choices:
                            msg = choices[0].get("message") or {}
                            content = msg.get("content")
                    except Exception:
                        content = None

                    parsed = None
                    if isinstance(content, str):
                        try:
                            parsed = _json.loads(content)
                        except Exception:
                            parsed = None

                    if isinstance(parsed, dict):
                        parsed.setdefault("source", "openrouter")
                        return {
                            "status": "ok",
                            "parsed": parsed,
                            "source": "openrouter",
                        }

                    if isinstance(data, dict):
                        data.setdefault("source", "openrouter")
                        if "parsed" in data or "status" in data:
                            return data
                        return {"status": "ok", "parsed": data, "source": "openrouter"}
            except Exception as e:
                logger.exception("OpenRouter insights-ml call failed: %s", e)
        else:
            logger.info(
                "analyze_ml_results: skipping OpenRouter, missing config (base_url=%s, key_is_none=%s)",
                base_url,
                key is None,
            )
    except Exception as e:
        logger.exception("OpenRouter chat call failed: %s", e)
    return None
