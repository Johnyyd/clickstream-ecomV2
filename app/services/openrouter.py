"""
OpenRouter AI service
"""
import httpx
from typing import Dict, Optional
from app.core.config import settings

async def analyze_user_behavior(user_id: str, api_key: str, db) -> Dict:
    """
    Analyze user behavior patterns using OpenRouter AI
    """
    user_data = await db.events.get_user_events(user_id)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OPENROUTER_API_URL}/analyze",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"user_data": user_data}
        )
        response.raise_for_status()
        return response.json()

async def analyze_ml_results(ml_results: Dict, api_key: Optional[str] = None) -> Dict:
    """
    Summarize existing ML analytics outputs (segmentation, retention, recommendations, etc.)
    using the OpenRouter backend if configured. If not configured, return a basic fallback
    summary so the UI still shows something.

    Args:
        ml_results: Dict of module results as computed by Spark jobs
        api_key: Optional override. If None, will try to use settings.OPENROUTER_API_KEY

    Returns:
        Dict containing a 'insights' narrative and optional 'highlights' bullets
    """
    try:
        base_url = getattr(settings, "OPENROUTER_API_URL", None)
        key = api_key or getattr(settings, "OPENROUTER_API_KEY", None)

        if base_url and key:
            # Build a concise system-style prompt describing what to do with module results
            prompt = (
                "You are an analytics expert. Summarize the provided module results into a clear business report. "
                "Return STRICT JSON with fields: 'executive_summary' (string), 'kpis' (object with optional "
                "'total_events','total_sessions','bounce_rate','avg_session_duration_seconds'), 'key_insights' (array of strings), "
                "'traffic_insights' (object with optional arrays), 'conversion_analysis' (object with 'funnel_performance', 'drop_off_points', 'optimization_opportunities' arrays), "
                "'recommendations' (array of strings), 'decisions' (array of strings), 'next_best_actions' (array of strings), "
                "'risk_alerts' (array of strings), 'recommendations_for_user' (array of strings), 'recommendations_for_user_products' (array of objects with 'product_id','name','reason'). "
                "Keep it concise and actionable."
            )
            async with httpx.AsyncClient(timeout=60) as client:
                # Assume the backend exposes a generic insights endpoint for ML summaries
                resp = await client.post(
                    f"{base_url}/insights-ml",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "prompt": prompt,
                        "results": ml_results,
                        "format": "json"
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                # Normalize to expected shape for llmDisplay.js when possible
                if isinstance(data, dict) and ("parsed" in data or "status" in data):
                    return data
                return {"status": "ok", "parsed": data}

        # Fallback: generate a lightweight local summary
        summary_lines = []
        if isinstance(ml_results, dict):
            for name, res in ml_results.items():
                if isinstance(res, dict) and "error" in res:
                    summary_lines.append(f"{name}: error - {res['error']}")
                elif isinstance(res, dict):
                    keys = ", ".join(list(res.keys())[:5])
                    summary_lines.append(f"{name}: ok ({keys})")
                else:
                    summary_lines.append(f"{name}: ok")
        # Shape fallback to match llmDisplay.js expectations
        parsed = {
            "executive_summary": ("\n".join(summary_lines) or "No ML results available"),
            "key_insights": summary_lines,
        }
        return {"status": "ok", "parsed": parsed}
    except Exception as e:
        return {"error": str(e), "insights": "Failed to generate LLM insights"}

async def generate_recommendations(user_id: str, api_key: str, db) -> Dict:
    """
    Generate personalized recommendations using OpenRouter AI
    """
    user_data = await db.events.get_user_events(user_id)
    product_data = await db.products.get_all()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OPENROUTER_API_URL}/recommend",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "user_data": user_data,
                "products": product_data
            }
        )
        response.raise_for_status()
        return response.json()

async def get_insights(user_id: str, api_key: str, db) -> Dict:
    """
    Get AI-generated insights about user behavior
    """
    user_data = await db.events.get_user_events(user_id)
    session_data = await db.events.get_user_sessions(user_id)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.OPENROUTER_API_URL}/insights",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "user_data": user_data,
                "sessions": session_data
            }
        )
        response.raise_for_status()
        return response.json()