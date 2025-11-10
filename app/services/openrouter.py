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
            # System-style prompt: require deeper, quantitative insights grouped by modules with prioritized actions
            prompt = (
                "You are a senior analytics expert. Given JSON analytics results from modules: business, journey, seo, retention, "
                "produce a concise yet deep report that helps a stakeholder understand performance and what to do next.\n"
                "Return STRICT JSON only with this schema: {\n"
                "  'executive_summary': string,\n"
                "  'kpis': { 'total_sessions'?: number, 'total_users'?: number, 'revenue'?: number, 'conversion_rate'?: number },\n"
                "  'insights': {\n"
                "     'business': { 'bullets': string[], 'revenue_drivers'?: { 'driver': string, 'contribution_pct': number }[] },\n"
                "     'journey': { 'bullets': string[], 'top_dropoffs'?: { 'from': string, 'to': string, 'rate': number }[], 'time_to_convert'?: { 'avg'?: number, 'p50'?: number, 'p90'?: number } },\n"
                "     'seo': { 'bullets': string[], 'top_sources'?: { 'source': string, 'share_pct': number }[], 'top_pages'?: { 'page': string, 'views': number }[], 'top_keywords'?: { 'term': string, 'share_pct': number }[], 'technical_issues'?: string[] },\n"
                "     'retention': { 'bullets': string[], 'cohort_summary'?: { 'cohort': string, 'retention_pct': number }[], 'churn_drivers'?: string[] }\n"
                "  },\n"
                "  'conversion_analysis': { 'funnel_performance': string[], 'drop_off_points': string[], 'optimization_opportunities': string[] },\n"
                "  'traffic_insights': { 'top_sources'?: string[], 'landing_pages'?: string[], 'top_pages'?: string[] },\n"
                "  'data_quality': { 'completeness_notes'?: string[], 'anomalies'?: string[], 'freshness'?: string[] },\n"
                "  'risk_alerts': { 'title': string, 'severity': 'low'|'medium'|'high', 'reason': string }[],\n"
                "  'next_best_actions': { 'action': string, 'impact': 'low'|'medium'|'high', 'effort': 'low'|'medium'|'high' }[],\n"
                "  'recommendations': string[],\n"
                "  'decisions': string[]\n"
                "}.\n"
                "Rules:\n"
                "- Be quantitative where possible (rates, shares, top-N). Compute drop-off rates between funnel steps if available.\n"
                "- Prioritize actions by impact vs. effort; avoid generic phrases.\n"
                "- Do not invent numbers. If a field/data is missing, omit that field.\n"
                "- Each bullet <= 18 words.\n"
                "- Output JSON only, no extra text."
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

        # Fallback: compute concrete insights locally (no OpenRouter)
        def _num(x):
            try:
                return float(x)
            except Exception:
                return 0.0

        business = (ml_results or {}).get("business") or {}
        journey = (ml_results or {}).get("journey") or {}
        seo = (ml_results or {}).get("seo") or {}
        retention = (ml_results or {}).get("retention") or {}

        # KPIs
        sessions = _num(business.get("total_sessions") or business.get("sessions") or 0)
        users = _num(business.get("total_users") or business.get("users") or 0)
        revenue = _num(business.get("revenue") or 0)
        cr = _num(business.get("conversion_rate") or 0)
        if sessions <= 0:
            views = _num(((seo.get("site_metrics") or {}).get("total_views")) or 0)
            if views > 0:
                sessions = views

        # Funnel + drop-offs
        funnel_steps = []  # [(name,value)]
        jf = journey.get("funnel")
        if isinstance(jf, dict) and isinstance(jf.get("steps"), list):
            for s in jf["steps"]:
                name = s.get("name") or s.get("step") or ""
                val = _num(s.get("value") or s.get("count") or 0)
                if name:
                    funnel_steps.append((name, val))
        elif isinstance(jf, dict):
            for k, v in jf.items():
                funnel_steps.append((str(k), _num(v)))

        drop_insights = []  # strings
        if len(funnel_steps) >= 2:
            for i in range(len(funnel_steps)-1):
                a, av = funnel_steps[i]
                b, bv = funnel_steps[i+1]
                rate = (1 - (bv/av)) if av > 0 else 0
                drop_insights.append((rate, f"Drop from {a} to {b}: {round(rate*100,2)}%"))
            drop_insights.sort(key=lambda x: x[0], reverse=True)
        top_drop = drop_insights[0][1] if drop_insights else None

        # Top sources
        top_sources = []
        try:
            dist = ((seo.get("sources") or {}).get("distribution")) or {}
            if isinstance(dist, dict):
                total = sum(_num(v) for v in dist.values()) or 1
                top_sources = [f"{k}: {round((_num(v)/total)*100,2)}%" for k, v in sorted(dist.items(), key=lambda kv: _num(kv[1]), reverse=True)[:5]]
        except Exception:
            top_sources = []

        # Retention quick facts
        ret_notes = []
        try:
            ts = retention.get("timeseries")
            if isinstance(ts, list) and ts:
                last = ts[-1]
                ret = _num(last.get("retained") or 0)
                ch = _num(last.get("churned") or 0)
                total = ret + ch if (ret+ch) > 0 else 1
                ret_notes.append(f"Latest retention: {round((ret/total)*100,2)}%")
        except Exception:
            pass

        # Key insights bullets
        insights = []
        if sessions:
            insights.append(f"Sessions: {int(sessions):,}")
        if users:
            insights.append(f"Users: {int(users):,}")
        if cr:
            insights.append(f"Conversion rate: {round(cr*100,2)}%")
        if revenue:
            insights.append(f"Revenue: ${round(revenue,2):,.2f}")
        if top_drop:
            insights.append(top_drop)
        if top_sources:
            insights.append("Top sources • " + "; ".join(top_sources))
        insights.extend(ret_notes)

        # Recommendations heuristics
        recs = []
        if top_drop:
            recs.append("Investigate top drop-off path; fix UX or messaging at that step")
        if top_sources:
            recs.append("Double down on top channels; A/B landing pages for weaker sources")
        if not revenue and sessions > 0 and cr == 0:
            recs.append("No conversions with traffic; verify tracking or checkout flow")

        summary_bits = []
        if sessions: summary_bits.append(f"Sessions {int(sessions):,}")
        if users: summary_bits.append(f"Users {int(users):,}")
        if cr: summary_bits.append(f"CR {round(cr*100,2)}%")
        if revenue: summary_bits.append(f"Revenue ${round(revenue,2):,.2f}")
        if top_drop: summary_bits.append(top_drop)

        parsed = {
            "executive_summary": "; ".join(summary_bits) or "No ML results available",
            "key_insights": insights or ["Insufficient data"],
            "recommendations": recs or ["Collect more data to generate actionable recommendations"],
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