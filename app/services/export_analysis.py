# export_analysis_data.py - Export analysis data to JSON for further analysis
from db import analyses_col
from bson import ObjectId
import json
from datetime import datetime

def export_analysis_data():
    print("=== Exporting Analysis Data ===")
    
    # Get all detailed analyses
    analyses = list(analyses_col().find(
        {"analysis_metadata.analysis_version": "2.0"},
        sort=[("created_at", -1)]
    ))
    
    if not analyses:
        print("No detailed analyses found")
        return
    
    print(f"Found {len(analyses)} detailed analyses")
    
    # Export each analysis
    for i, analysis in enumerate(analyses):
        # Convert ObjectId to string for JSON serialization
        analysis_export = {
            "analysis_id": str(analysis["_id"]),
            "user_id": str(analysis["user_id"]),
            "created_at": analysis["created_at"].isoformat(),
            "parameters": analysis.get("parameters", {}),
            "status": analysis.get("status", ""),
            
            # Basic summary
            "spark_summary": analysis.get("spark_summary", {}),
            
            # Detailed metrics
            "detailed_metrics": analysis.get("detailed_metrics", {}),
            
            # Insights
            "insights": analysis.get("insights", {}),
            
            # Analysis metadata
            "analysis_metadata": analysis.get("analysis_metadata", {}),
            
            # LLM output (if available)
            "openrouter_output": analysis.get("openrouter_output")
        }
        
        # Save to file
        filename = f"analysis_export_{i+1}_{analysis['_id']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_export, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"Exported analysis {i+1} to {filename}")
        
        # Show summary
        spark_summary = analysis_export.get("spark_summary", {})
        detailed_metrics = analysis_export.get("detailed_metrics", {})
        basic_metrics = detailed_metrics.get("basic_metrics", {})
        
        print(f"  - Events: {spark_summary.get('total_events', 0)}")
        print(f"  - Sessions: {spark_summary.get('sessions', 0)}")
        print(f"  - Users: {basic_metrics.get('unique_users', 0)}")
        print(f"  - Bounce Rate: {basic_metrics.get('bounce_rate', 0):.2%}")
        print()
    
    # Create a summary file
    summary = {
        "export_timestamp": datetime.now().isoformat(),
        "total_analyses": len(analyses),
        "analyses": [
            {
                "analysis_id": str(a["_id"]),
                "created_at": a["created_at"].isoformat(),
                "total_events": a.get("spark_summary", {}).get("total_events", 0),
                "total_sessions": a.get("spark_summary", {}).get("sessions", 0),
                "unique_users": a.get("detailed_metrics", {}).get("basic_metrics", {}).get("unique_users", 0),
                "bounce_rate": a.get("detailed_metrics", {}).get("basic_metrics", {}).get("bounce_rate", 0)
            }
            for a in analyses
        ]
    }
    
    with open("analysis_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Created analysis_summary.json with overview of all analyses")
    print(f"\n✅ Export completed! You can now use these JSON files for:")
    print(f"  - Data visualization")
    print(f"  - Further statistical analysis")
    print(f"  - Machine learning models")
    print(f"  - Business intelligence dashboards")
    print(f"  - Trend analysis over time")

if __name__ == "__main__":
    export_analysis_data()
