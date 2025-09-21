# analysis.py
from simple_analysis import simple_sessionize_and_counts
from openrouter_client import call_openrouter
from db import analyses_col, api_keys_col, events_col
from bson import ObjectId
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import statistics

def calculate_detailed_metrics(limit=None):
    """Calculate detailed metrics for deeper analysis"""
    try:
        # Load events from MongoDB
        q = {}
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
        print("Running basic analysis...")
        spark_summary = simple_sessionize_and_counts(limit=params.get("limit"))
        print("Basic analysis completed successfully")
    except Exception as e:
        print(f"Error in basic analysis: {str(e)}")
        error_record = {
            "user_id": ObjectId(user_id),
            "created_at": datetime.utcnow(),
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
        detailed_metrics = calculate_detailed_metrics(limit=params.get("limit"))
        print("Detailed analysis completed successfully")
    except Exception as e:
        print(f"Error in detailed analysis: {str(e)}")
        detailed_metrics = {}

    # 3. Generate insights and recommendations
    insights = generate_insights(spark_summary, detailed_metrics)
    
    # 4. Prepare comprehensive analysis record
    analysis_record = {
        "user_id": ObjectId(user_id),
        "created_at": datetime.utcnow(),
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

    # 5. Check for OpenRouter API key for LLM analysis
    print("Checking for OpenRouter API key...")
    key_doc = api_keys_col().find_one({"user_id": ObjectId(user_id), "provider": "openrouter"})
    
    if key_doc:
        print("Found OpenRouter API key, proceeding with LLM analysis")
        api_key = key_doc["key_encrypted"]
        
        # Prepare enhanced prompt with detailed metrics
        prompt = f"""
        I have comprehensive clickstream analysis results:
        
        Basic Summary: {json.dumps(spark_summary, default=str)}
        
        Detailed Metrics: {json.dumps(detailed_metrics, default=str, indent=2)}
        
        Please provide:
        1) Executive summary (3-4 sentences)
        2) Key insights and patterns
        3) Conversion funnel analysis
        4) User behavior insights
        5) Recommendations for improvement
        6) Suggested next analysis steps
        """
        
        try:
            print("Calling OpenRouter API...")
            llm_response = call_openrouter(api_key, prompt)
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
