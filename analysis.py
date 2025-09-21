# analysis.py
from simple_analysis import simple_sessionize_and_counts
from openrouter_client import call_openrouter
from db import analyses_col, api_keys_col
from bson import ObjectId
import json
from datetime import datetime

def run_analysis(user_id, params):
    print(f"\n=== Starting Analysis for User {user_id} ===")
    # 1. run simple analysis (replacing Spark)
    try:
        print("Running simple analysis...")
        spark_summary = simple_sessionize_and_counts(limit=params.get("limit"))
        print("Simple analysis completed successfully")
        print("Summary:", spark_summary)
    except Exception as e:
        print(f"Error in simple analysis: {str(e)}")
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

    # 2. prepare prompt
    prompt = f"""
    I have clickstream analysis results in JSON: {json.dumps(spark_summary, default=str)}
    Please produce:
    1) A short executive summary (3-4 sentences)
    2) A detailed breakdown: top pages, sessions, funnel interpretation
    3) Suggested next steps and queries to run in Spark.
    """
    print("Prepared analysis prompt")

    # 3. find user's OpenRouter key
    print("Checking for OpenRouter API key...")
    key_doc = api_keys_col().find_one({"user_id": ObjectId(user_id), "provider": "openrouter"})
    if not key_doc:
        print("No OpenRouter API key found, saving analysis without LLM processing")
        # don't call LLM, just save spark_summary and mark pending LLM
        rec = {
            "user_id": ObjectId(user_id),
            "created_at": datetime.utcnow(),
            "parameters": params,
            "spark_summary": spark_summary,
            "openrouter_output": None,
            "status": "done"
        }
        result = analyses_col().insert_one(rec)
        print(f"Saved analysis record with ID: {result.inserted_id}")
        rec["_id"] = result.inserted_id
        return rec

    print("Found OpenRouter API key, proceeding with LLM analysis")
    api_key = key_doc["key_encrypted"]  # in prod decrypt
    try:
        print("Calling OpenRouter API...")
        lresp = call_openrouter(api_key, prompt)
        print("OpenRouter API call successful")
    except Exception as e:
        print(f"Error calling OpenRouter: {str(e)}")
        rec = {
            "user_id": ObjectId(user_id),
            "created_at": datetime.utcnow(),
            "parameters": params,
            "spark_summary": spark_summary,
            "openrouter_output": {"error": str(e)},
            "status": "done"
        }
        result = analyses_col().insert_one(rec)
        print(f"Saved error record with ID: {result.inserted_id}")
        rec["_id"] = result.inserted_id
        return rec

    print("Creating final analysis record")
    rec = {
        "user_id": ObjectId(user_id),
        "created_at": datetime.utcnow(),
        "parameters": params,
        "spark_summary": spark_summary,
        "openrouter_output": lresp,
        "status": "done"
    }
    result = analyses_col().insert_one(rec)
    print(f"Saved final analysis record with ID: {result.inserted_id}")
    rec["_id"] = result.inserted_id
    return rec
