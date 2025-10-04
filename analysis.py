def simple_sessionize_and_counts(limit=None, user_id=None):
    """Basic, fast analysis over events for quick stats.
    Uses Spark if USE_SPARK is enabled, otherwise falls back to Python implementation.

    Returns dict with keys: total_events, sessions, events_by_type, top_pages.
    """
    if USE_SPARK:
        try:
            from spark_jobs import sessionize_and_counts
            print("Using Spark for analysis...")
            result = sessionize_and_counts(limit=limit)
            
            # Convert Spark result to match the Python implementation's format
            events_by_type = {}
            if "events_by_type" in result:
                events_by_type = result["events_by_type"]
            
            top_pages = []
            if "top_pages" in result:
                top_pages = [(page, count) for page, count in result["top_pages"].items()]
            
            return {
                "total_events": result.get("total_events", 0),
                "sessions": result.get("sessions", 0),
                "events_by_type": events_by_type,
                "top_pages": top_pages,
                "funnel_metrics": result.get("funnel_metrics", {}),
                "conversion_rates": result.get("conversion_rates", {}),
                "session_metrics": result.get("session_metrics", {})
            }
        except Exception as e:
            print(f"Error in Spark analysis: {str(e)}")
            print("Falling back to Python implementation...")
            # Continue to Python implementation as fallback
    
    # Python implementation (fallback)
    try:
        q = {}
        if user_id is not None:
            try:
                oid = ObjectId(str(user_id))
                q["$or"] = [{"user_id": oid}, {"user_id": str(user_id)}]
            except Exception:
                q["user_id"] = str(user_id)

        cursor = events_col().find(q).sort("timestamp", 1)
        if limit:
            cursor = cursor.limit(int(limit))

        total = 0
        sessions = set()
        events_by_type = Counter()
        page_counts = Counter()

        for ev in cursor:
            total += 1
            sid = str(ev.get("session_id", ""))
            if sid:
                sessions.add(sid)
            et = str(ev.get("event_type", "pageview"))
            if et:
                events_by_type[et] += 1
            pg = str(ev.get("page", ""))
            if pg:
                page_counts[pg] += 1

        return {
            "total_events": total,
            "sessions": len(sessions),
            "events_by_type": dict(events_by_type),
            "top_pages": page_counts.most_common(10),
            "funnel_metrics": {},
            "conversion_rates": {},
            "session_metrics": {}
        }
    except Exception as e:
        # Return minimal structure so callers don't crash
        return {
            "total_events": 0, 
            "sessions": 0, 
            "events_by_type": {}, 
            "top_pages": [],
            "funnel_metrics": {},
            "conversion_rates": {},
            "session_metrics": {}
        }
# analysis.py
import os
from openrouter_client import call_openrouter
from db import analyses_col, api_keys_col, events_col, products_col, users_col
from bson import ObjectId
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import statistics
import pytz 

# Feature flag to enable/disable Spark analysis
USE_SPARK = os.environ.get('USE_SPARK', 'false').lower() == 'true'

def _coerce_llm_parsed(parsed, spark_summary, detailed_metrics, generated_insights):
    """Ensure LLM parsed output has required keys and fill sensible defaults.

    Required keys:
      - executive_summary: str
      - key_insights: [str]
      - recommendations: [str]
      - decisions: [str]
      - next_best_actions: [str]
      - risk_alerts: [str]
      - kpis: { total_events, total_sessions, bounce_rate, avg_session_duration_seconds }
    """
    if not isinstance(parsed, dict):
        parsed = {}

    basic = detailed_metrics.get("basic_metrics", {}) if isinstance(detailed_metrics, dict) else {}
    total_events = basic.get("total_events", spark_summary.get("total_events", 0)) if isinstance(spark_summary, dict) else 0
    total_sessions = basic.get("total_sessions", spark_summary.get("sessions", 0)) if isinstance(spark_summary, dict) else 0
    bounce_rate = basic.get("bounce_rate", 0)
    avg_sess = basic.get("avg_session_duration_seconds", 0)

    def _list_or_default(val, default):
        return val if isinstance(val, list) else list(default)

    # Fall back to generated Python insights
    py_key_insights = generated_insights.get("key_findings", []) if isinstance(generated_insights, dict) else []
    py_recs = generated_insights.get("recommendations", []) if isinstance(generated_insights, dict) else []

    # Prefer explicit user-facing recs if provided by the LLM, otherwise fall back to Python-generated recs
    recs_for_user = None
    try:
        if isinstance(parsed, dict):
            rfu = parsed.get("recommendations_for_user")
            if isinstance(rfu, list):
                recs_for_user = rfu
    except Exception:
        pass

    coerced = {
        "executive_summary": parsed.get("executive_summary") or "Automated summary not provided by LLM.",
        "key_insights": _list_or_default(parsed.get("key_insights"), py_key_insights),
        "recommendations": _list_or_default(parsed.get("recommendations"), py_recs),
        "recommendations_for_user": _list_or_default(recs_for_user, py_recs),
        "decisions": _list_or_default(parsed.get("decisions"), []),
        "next_best_actions": _list_or_default(parsed.get("next_best_actions"), []),
        "risk_alerts": _list_or_default(parsed.get("risk_alerts"), []),
        "kpis": {
            "total_events": (parsed.get("kpis") or {}).get("total_events", total_events),
            "total_sessions": (parsed.get("kpis") or {}).get("total_sessions", total_sessions),
            "bounce_rate": (parsed.get("kpis") or {}).get("bounce_rate", bounce_rate),
            "avg_session_duration_seconds": (parsed.get("kpis") or {}).get("avg_session_duration_seconds", avg_sess),
        }
    }
    return coerced

def _coerce_product_recs(product_recs, product_index):
    """Validate and normalize product recommendations list.
    product_recs: list of {product_id, name, reason}
    product_index: dict of str(ObjectId) -> product dict
    """
    out = []
    if not isinstance(product_recs, list):
        return out
    for item in product_recs:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("product_id", ""))
        reason = str(item.get("reason", "")) if item.get("reason") else "Recommended based on browsing and purchase intent."
        prod = product_index.get(pid)
        if not prod:
            continue
        out.append({
            "product_id": pid,
            "name": prod.get("name"),
            "category": prod.get("category"),
            "price": prod.get("price"),
            "tags": prod.get("tags", []),
            "reason": reason
        })
    return out

def _build_user_context(detailed_metrics):
    """Summarize user behavior context from detailed_metrics for the LLM prompt."""
    try:
        basic = detailed_metrics.get("basic_metrics", {})
        funnels = detailed_metrics.get("funnel_analysis", {})
        top_pages = detailed_metrics.get("page_analysis", {}).get("top_pages", [])
        top_events = detailed_metrics.get("event_analysis", {}).get("top_event_types", [])
        ctx = {
            "basic": basic,
            "funnels": funnels,
            "top_pages": top_pages[:10],
            "top_events": top_events[:10],
        }
        return ctx
    except Exception:
        return {}

def calculate_detailed_metrics(limit=None, user_id=None):
    """Calculate detailed metrics for deeper analysis"""
    try:
        # Load events from MongoDB
        q = {}
        if user_id is not None:
            # Support both ObjectId and string stored user_id
            try:
                oid = ObjectId(str(user_id))
                q["$or"] = [{"user_id": oid}, {"user_id": str(user_id)}]
            except Exception:
                q["user_id"] = str(user_id)
        # Exclude flagged noisy data and known demo sources
        base_filters = {
            "flag.noisy": {"$ne": True},
            "$or": [
                {"properties.source": {"$exists": False}},
                {"properties.source": {"$nin": ["simulation", "basic_sim", "seed_demo"]}},
            ],
        }
        if q:
            q = {"$and": [q, base_filters]}
        else:
            q = base_filters

        cursor = events_col().find(q).sort("timestamp", 1)
        if limit:
            cursor = cursor.limit(limit)
        
        events = list(cursor)
        print(f"Calculating detailed metrics for {len(events)} events")
        
        if not events:
            return {}
        
        # Basic metrics
        total_events = len(events)
        sessions = set()
        page_counts = Counter()
        event_type_counts = Counter()
        hourly_distribution = defaultdict(int)
        daily_distribution = defaultdict(int)
        session_lengths = defaultdict(list)
        page_sequences = defaultdict(list)
        user_behavior = defaultdict(lambda: {"sessions": set(), "pages": [], "events": 0})
        
        # Process events
        for event in events:
            session_id = str(event.get("session_id", ""))
            page = str(event.get("page", ""))
            event_type = str(event.get("event_type", "pageview"))
            user_id = str(event.get("user_id", ""))
            timestamp = event.get("timestamp")
            
            if session_id:
                sessions.add(session_id)
                session_lengths[session_id].append(timestamp)
                page_sequences[session_id].append(page)
            
            if page:
                page_counts[page] += 1
            
            if event_type:
                event_type_counts[event_type] += 1
            
            if user_id:
                user_behavior[user_id]["sessions"].add(session_id)
                user_behavior[user_id]["pages"].append(page)
                user_behavior[user_id]["events"] += 1
            
            # Time distribution
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        try:
                            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            continue
                
                if isinstance(timestamp, datetime):
                    hourly_distribution[timestamp.hour] += 1
                    daily_distribution[timestamp.strftime("%Y-%m-%d")] += 1
        
        # Calculate session metrics
        session_metrics = {}
        for session_id, timestamps in session_lengths.items():
            if len(timestamps) > 1:
                timestamps.sort()
                duration = (timestamps[-1] - timestamps[0]).total_seconds()
                session_metrics[session_id] = {
                    "duration_seconds": duration,
                    "page_count": len(page_sequences[session_id]),
                    "unique_pages": len(set(page_sequences[session_id]))
                }
        
        # Calculate user metrics
        user_metrics = {}
        for user_id, behavior in user_behavior.items():
            if behavior["sessions"]:
                user_metrics[user_id] = {
                    "total_sessions": len(behavior["sessions"]),
                    "total_events": behavior["events"],
                    "unique_pages": len(set(behavior["pages"])),
                    "avg_events_per_session": behavior["events"] / len(behavior["sessions"])
                }
        
        # Calculate funnel metrics
        funnel_metrics = calculate_funnel_analysis(page_sequences)
        
        # Calculate conversion rates
        conversion_rates = calculate_conversion_rates(page_sequences)
        
        # Calculate bounce rate
        bounce_rate = calculate_bounce_rate(session_metrics)
        
        # Calculate average session duration
        avg_session_duration = statistics.mean([s["duration_seconds"] for s in session_metrics.values()]) if session_metrics else 0
        
        # Calculate pages per session
        avg_pages_per_session = statistics.mean([s["page_count"] for s in session_metrics.values()]) if session_metrics else 0
        
        detailed_metrics = {
            "basic_metrics": {
                "total_events": total_events,
                "total_sessions": len(sessions),
                "unique_users": len(user_behavior),
                "avg_session_duration_seconds": round(avg_session_duration, 2),
                "avg_pages_per_session": round(avg_pages_per_session, 2),
                "bounce_rate": round(bounce_rate, 4)
            },
            "page_analysis": {
                "top_pages": [{"page": page, "count": count} for page, count in page_counts.most_common(20)],
                "page_distribution": {str(k): v for k, v in page_counts.items()}
            },
            "event_analysis": {
                "event_types": {str(k): v for k, v in event_type_counts.items()},
                "top_event_types": [{"type": event_type, "count": count} for event_type, count in event_type_counts.most_common(10)]
            },
            "time_analysis": {
                "hourly_distribution": {str(k): v for k, v in hourly_distribution.items()},
                "daily_distribution": {str(k): v for k, v in daily_distribution.items()},
                "peak_hour": max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else None,
                "peak_day": max(daily_distribution.items(), key=lambda x: x[1])[0] if daily_distribution else None
            },
            "session_analysis": {
                "session_metrics": session_metrics,
                "avg_session_duration": round(avg_session_duration, 2),
                "avg_pages_per_session": round(avg_pages_per_session, 2)
            },
            "user_analysis": {
                "user_metrics": user_metrics,
                "avg_sessions_per_user": statistics.mean([u["total_sessions"] for u in user_metrics.values()]) if user_metrics else 0,
                "avg_events_per_user": statistics.mean([u["total_events"] for u in user_metrics.values()]) if user_metrics else 0
            },
            "funnel_analysis": funnel_metrics,
            "conversion_rates": conversion_rates
        }
        
        return detailed_metrics
        
    except Exception as e:
        print(f"Error calculating detailed metrics: {e}")
        return {}

def calculate_funnel_analysis(page_sequences):
    """Calculate detailed funnel analysis"""
    funnels = {
        "home_to_product": {"home": 0, "product": 0, "conversion": 0},
        "product_to_checkout": {"product": 0, "checkout": 0, "conversion": 0},
        "home_to_checkout": {"home": 0, "checkout": 0, "conversion": 0},
        "search_to_product": {"search": 0, "product": 0, "conversion": 0}
    }
    
    for session_id, pages in page_sequences.items():
        pages_set = set(pages)
        
        # Home to Product funnel
        if "/home" in pages_set:
            funnels["home_to_product"]["home"] += 1
            if "/product" in pages_set:
                funnels["home_to_product"]["product"] += 1
        
        # Product to Checkout funnel
        if "/product" in pages_set:
            funnels["product_to_checkout"]["product"] += 1
            if "/checkout" in pages_set:
                funnels["product_to_checkout"]["checkout"] += 1
        
        # Home to Checkout funnel
        if "/home" in pages_set:
            funnels["home_to_checkout"]["home"] += 1
            if "/checkout" in pages_set:
                funnels["home_to_checkout"]["checkout"] += 1
        
        # Search to Product funnel
        if "/search" in pages_set:
            funnels["search_to_product"]["search"] += 1
            if "/product" in pages_set:
                funnels["search_to_product"]["product"] += 1
    
    # Calculate conversion rates
    for funnel_name, funnel_data in funnels.items():
        if funnel_data.get("home", 0) > 0 or funnel_data.get("product", 0) > 0 or funnel_data.get("search", 0) > 0:
            if funnel_name == "home_to_product":
                funnel_data["conversion"] = funnel_data["product"] / funnel_data["home"] if funnel_data["home"] > 0 else 0
            elif funnel_name == "product_to_checkout":
                funnel_data["conversion"] = funnel_data["checkout"] / funnel_data["product"] if funnel_data["product"] > 0 else 0
            elif funnel_name == "home_to_checkout":
                funnel_data["conversion"] = funnel_data["checkout"] / funnel_data["home"] if funnel_data["home"] > 0 else 0
            elif funnel_name == "search_to_product":
                funnel_data["conversion"] = funnel_data["product"] / funnel_data["search"] if funnel_data["search"] > 0 else 0
    
    return funnels

def calculate_conversion_rates(page_sequences):
    """Calculate various conversion rates"""
    total_sessions = len(page_sequences)
    if total_sessions == 0:
        return {}
    
    conversions = {}
    
    # Page visit rates
    page_visits = defaultdict(int)
    for pages in page_sequences.values():
        for page in set(pages):
            page_visits[page] += 1
    
    conversions["page_visit_rates"] = {
        str(page): count / total_sessions 
        for page, count in page_visits.items()
    }
    
    # Multi-page session rate
    multi_page_sessions = sum(1 for pages in page_sequences.values() if len(set(pages)) > 1)
    conversions["multi_page_session_rate"] = multi_page_sessions / total_sessions
    
    # Return visitor rate (sessions with multiple visits to same page)
    return_visitor_sessions = 0
    for pages in page_sequences.values():
        if len(pages) > len(set(pages)):  # Has duplicate pages
            return_visitor_sessions += 1
    conversions["return_visitor_rate"] = return_visitor_sessions / total_sessions
    
    return conversions

def calculate_bounce_rate(session_metrics):
    """Calculate bounce rate (sessions with only 1 page)"""
    if not session_metrics:
        return 0
    
    single_page_sessions = sum(1 for s in session_metrics.values() if s["page_count"] == 1)
    return single_page_sessions / len(session_metrics)

def run_analysis(user_id, params):
    print(f"\n=== Starting Analysis for User {user_id} ===")
    
    # 1. Run basic analysis
    try:
        print(f"Running {'Spark' if USE_SPARK else 'Python'} analysis...")
        spark_summary = simple_sessionize_and_counts(limit=params.get("limit"), user_id=user_id)
        print(f"Analysis completed successfully (using {'Spark' if USE_SPARK else 'Python'})")
    except Exception as e:
        print(f"Error in basic analysis: {str(e)}")
        error_record = {
            "user_id": ObjectId(user_id),
            "created_at": datetime.now(pytz.UTC),
            "parameters": params,
            "status": "failed",
            "error": str(e)
        }
        result = analyses_col().insert_one(error_record)
        print(f"Saved error record with ID: {result.inserted_id}")
        raise

    # 2. Run detailed analysis
    try:
        print("Running detailed analysis...")
        detailed_metrics = calculate_detailed_metrics(limit=params.get("limit"), user_id=user_id)
        print("Detailed analysis completed successfully")
    except Exception as e:
        print(f"Error in detailed analysis: {str(e)}")
        detailed_metrics = {}

    # 3. Generate insights and recommendations
    insights = generate_insights(spark_summary, detailed_metrics)
    
    # 4. Prepare comprehensive analysis record
    analysis_record = {
        "user_id": ObjectId(user_id),
        "created_at": datetime.now(pytz.UTC),
        "parameters": params,
        "status": "done",
        
        # Basic metrics (for backward compatibility)
        "spark_summary": spark_summary,
        
        # Detailed metrics for deeper analysis
        "detailed_metrics": detailed_metrics,
        
        # Generated insights
        "insights": insights,
        
        # Analysis metadata
        "analysis_metadata": {
            "data_period": {
                "start_date": None,  # Will be calculated from events
                "end_date": None,
                "total_days": 0
            },
            "data_quality": {
                "total_events": detailed_metrics.get("basic_metrics", {}).get("total_events", 0),
                "total_sessions": detailed_metrics.get("basic_metrics", {}).get("total_sessions", 0),
                "unique_users": detailed_metrics.get("basic_metrics", {}).get("unique_users", 0),
                "bounce_rate": detailed_metrics.get("basic_metrics", {}).get("bounce_rate", 0)
            },
            "analysis_version": "2.0",
            "analysis_type": "comprehensive_clickstream"
        }
    }

    # Preload products and build indices for recommendation validation
    try:
        product_docs = list(products_col().find({}, {"name": 1, "category": 1, "price": 1, "tags": 1}))
    except Exception:
        product_docs = []
    product_index = {str(p.get("_id")): p for p in product_docs}
    # Prepare a trimmed catalog snapshot for the prompt to keep it concise
    catalog_for_prompt = [
        {
            "_id": str(p.get("_id")),
            "name": p.get("name"),
            "category": p.get("category"),
            "price": p.get("price"),
            "tags": p.get("tags", []),
        }
        for p in product_docs[:50]
    ]

    # Build lightweight user context for LLM
    user_ctx = _build_user_context(detailed_metrics)

    # Load user's previous recommendation history (if any)
    try:
        user_doc = users_col().find_one({"_id": ObjectId(user_id)}, {"product_recommendations": 1})
        history = (user_doc or {}).get("product_recommendations", [])
    except Exception:
        history = []

    # 5. Check for OpenRouter API key for LLM analysis
    print("Checking for OpenRouter API key...")
    key_doc = api_keys_col().find_one({"user_id": ObjectId(user_id), "provider": "openrouter"})
    
    if key_doc:
        print("Found OpenRouter API key, proceeding with LLM analysis")
        api_key = key_doc["key_encrypted"]
        
        # Prepare enhanced prompt with detailed metrics
        prompt = f"""
        I have comprehensive clickstream analysis results and a product catalog.

        Basic Summary: {json.dumps(spark_summary, default=str)}

        Detailed Metrics: {json.dumps(detailed_metrics, default=str)[:4000]}

        User Context (summarized): {json.dumps(user_ctx, default=str)}

        Product Catalog (subset): {json.dumps(catalog_for_prompt, default=str)}

        Previous Recommendation History: {json.dumps(history[-3:], default=str)}

        Your task:
        - Provide executive summary and key insights.
        - Provide actionable recommendations for the business.
        - Provide the best recommendations for the user (3-5 sentences) using the catalog items only.
        - IMPORTANT: Also provide a structured list 'recommendations_for_user_products' with up to 5 items strictly from the catalog subset using their _id as product_id, plus name and a short reason.
        """
        
        try:
            print("Calling OpenRouter API...")
            llm_response = call_openrouter(api_key, prompt)
            # Enrich/validate parsed payload if present
            if isinstance(llm_response, dict) and llm_response.get("status") == "ok":
                parsed = llm_response.get("parsed")
                coerced = _coerce_llm_parsed(parsed, spark_summary, detailed_metrics, insights)
                # Validate product recommendations
                product_recs = []
                try:
                    product_recs = parsed.get("recommendations_for_user_products", []) if isinstance(parsed, dict) else []
                except Exception:
                    product_recs = []
                product_recs = _coerce_product_recs(product_recs, product_index)
                coerced["recommendations_for_user_products"] = product_recs
                llm_response["parsed"] = coerced
                # Also store top-level for easy querying
                analysis_record["product_recommendations"] = product_recs
                # Update user profile history for cross-session availability
                if product_recs:
                    try:
                        users_col().update_one(
                            {"_id": ObjectId(user_id)},
                            {"$push": {"product_recommendations": {
                                "created_at": datetime.now(pytz.UTC),
                                "items": product_recs
                            }}}
                        )
                    except Exception:
                        pass
            analysis_record["openrouter_output"] = llm_response
            print("LLM analysis completed successfully")
        except Exception as e:
            print(f"Error calling OpenRouter: {str(e)}")
            analysis_record["openrouter_output"] = {"error": str(e)}
    else:
        print("No OpenRouter API key found, saving analysis without LLM processing")
        analysis_record["openrouter_output"] = None

    # 6. Save comprehensive analysis record
    result = analyses_col().insert_one(analysis_record)
    print(f"Saved comprehensive analysis record with ID: {result.inserted_id}")
    analysis_record["_id"] = result.inserted_id
    
    return analysis_record

def generate_insights(spark_summary, detailed_metrics):
    """Generate insights from analysis data"""
    insights = {
        "key_findings": [],
        "recommendations": [],
        "alerts": [],
        "trends": []
    }
    
    # Extract basic metrics
    basic_metrics = detailed_metrics.get("basic_metrics", {})
    total_events = basic_metrics.get("total_events", 0)
    total_sessions = basic_metrics.get("total_sessions", 0)
    bounce_rate = basic_metrics.get("bounce_rate", 0)
    avg_session_duration = basic_metrics.get("avg_session_duration_seconds", 0)
    
    # Key findings
    if total_events > 0:
        insights["key_findings"].append(f"Total of {total_events} events across {total_sessions} sessions")
    
    if bounce_rate > 0.7:
        insights["key_findings"].append(f"High bounce rate of {bounce_rate:.1%} indicates potential UX issues")
    elif bounce_rate < 0.3:
        insights["key_findings"].append(f"Low bounce rate of {bounce_rate:.1%} shows good user engagement")
    
    if avg_session_duration > 300:  # 5 minutes
        insights["key_findings"].append(f"Good average session duration of {avg_session_duration/60:.1f} minutes")
    elif avg_session_duration < 60:  # 1 minute
        insights["key_findings"].append(f"Short average session duration of {avg_session_duration:.1f} seconds")
    
    # Funnel analysis insights
    funnel_analysis = detailed_metrics.get("funnel_analysis", {})
    for funnel_name, funnel_data in funnel_analysis.items():
        if funnel_data.get("conversion", 0) > 0:
            conversion_rate = funnel_data["conversion"]
            if conversion_rate > 0.3:
                insights["key_findings"].append(f"Strong {funnel_name} conversion rate of {conversion_rate:.1%}")
            elif conversion_rate < 0.1:
                insights["alerts"].append(f"Low {funnel_name} conversion rate of {conversion_rate:.1%}")
    
    # Page analysis insights
    page_analysis = detailed_metrics.get("page_analysis", {})
    top_pages = page_analysis.get("top_pages", [])
    if top_pages:
        most_visited = top_pages[0]
        insights["key_findings"].append(f"Most visited page: {most_visited['page']} ({most_visited['count']} visits)")
    
    # Time analysis insights
    time_analysis = detailed_metrics.get("time_analysis", {})
    peak_hour = time_analysis.get("peak_hour")
    if peak_hour is not None:
        insights["key_findings"].append(f"Peak traffic hour: {peak_hour}:00")
    
    # Recommendations
    if bounce_rate > 0.5:
        insights["recommendations"].append("Improve page content and user experience to reduce bounce rate")
    
    if avg_session_duration < 120:  # 2 minutes
        insights["recommendations"].append("Add more engaging content to increase session duration")
    
    # Check for low conversion funnels
    for funnel_name, funnel_data in funnel_analysis.items():
        if funnel_data.get("conversion", 0) < 0.1 and funnel_data.get("home", 0) > 10:
            insights["recommendations"].append(f"Optimize {funnel_name} funnel to improve conversion")
    
    return insights
