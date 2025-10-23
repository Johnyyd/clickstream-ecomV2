"""
Quick metrics checker to verify bounce rate and top pages
"""
from db import events_col, sessions_col

def check_bounce_rate():
    """Calculate current bounce rate"""
    total_sessions = sessions_col().count_documents({})
    
    # Count sessions with only 1 event
    bounce_sessions = list(events_col().aggregate([
        {"$group": {
            "_id": "$session_id",
            "event_count": {"$sum": 1}
        }},
        {"$match": {"event_count": 1}},
        {"$count": "total"}
    ]))
    
    bounces = bounce_sessions[0]["total"] if bounce_sessions else 0
    bounce_rate = (bounces / total_sessions * 100) if total_sessions > 0 else 0
    
    print("\n📊 Bounce Rate Analysis")
    print("="*50)
    print(f"Total Sessions:   {total_sessions:,}")
    print(f"Bounce Sessions:  {bounces:,}")
    print(f"Bounce Rate:      {bounce_rate:.2f}%")
    print(f"Target:           0.5%")
    print(f"Status:           {'✅ Good' if 0.4 <= bounce_rate <= 0.6 else '⚠️  Needs adjustment'}")
    print()

def check_top_pages():
    """Show top pages with view counts"""
    pipeline = [
        {"$group": {
            "_id": "$page",
            "views": {"$sum": 1}
        }},
        {"$sort": {"views": -1}},
        {"$limit": 20}
    ]
    
    results = list(events_col().aggregate(pipeline))
    
    print("\n📄 Top 20 Pages")
    print("="*70)
    
    product_pages = 0
    total_views = sum(r["views"] for r in results)
    
    for i, page in enumerate(results, 1):
        page_url = page["_id"]
        views = page["views"]
        pct = (views / total_views * 100) if total_views > 0 else 0
        
        # Check if product page
        is_product = page_url.startswith("/p/") or "/product/" in page_url
        marker = "🛍️ " if is_product else "   "
        
        if is_product:
            product_pages += 1
        
        print(f"{marker}{i:2d}. {page_url:50s} {views:6,} ({pct:5.1f}%)")
    
    print("="*70)
    print(f"Product Pages in Top 20: {product_pages}/20")
    print(f"Target: 10-15 product pages")
    print()

def check_event_distribution():
    """Show event type distribution"""
    pipeline = [
        {"$group": {
            "_id": "$event_type",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    results = list(events_col().aggregate(pipeline))
    total_events = sum(r["count"] for r in results)
    
    print("\n🎯 Event Type Distribution")
    print("="*50)
    
    for event in results:
        event_type = event["_id"]
        count = event["count"]
        pct = (count / total_events * 100) if total_events > 0 else 0
        print(f"{event_type:20s} {count:8,} ({pct:5.1f}%)")
    
    print("="*50)
    print(f"Total Events: {total_events:,}")
    print()

def check_product_views():
    """Analyze product view patterns"""
    # Count product page views
    product_views = events_col().count_documents({
        "$or": [
            {"page": {"$regex": "^/p/"}},
            {"page": {"$regex": "/product/"}}
        ]
    })
    
    total_events = events_col().count_documents({})
    
    # Get top viewed products
    pipeline = [
        {"$match": {
            "$or": [
                {"page": {"$regex": "^/p/"}},
                {"page": {"$regex": "/product/"}}
            ]
        }},
        {"$group": {
            "_id": "$properties.product_name",
            "views": {"$sum": 1},
            "page": {"$first": "$page"}
        }},
        {"$sort": {"views": -1}},
        {"$limit": 10}
    ]
    
    top_products = list(events_col().aggregate(pipeline))
    
    print("\n🛍️  Product View Analysis")
    print("="*70)
    print(f"Total Product Views: {product_views:,}")
    print(f"Total Events:        {total_events:,}")
    print(f"Product View Rate:   {(product_views/total_events*100):.1f}%")
    print(f"Target:              40-60%")
    print()
    
    if top_products:
        print("Top 10 Products:")
        for i, prod in enumerate(top_products, 1):
            name = prod["_id"] or "Unknown"
            views = prod["views"]
            print(f"  {i:2d}. {name:40s} {views:5,} views")
    print()

def main():
    print("\n" + "="*70)
    print("📊 CLICKSTREAM METRICS CHECKER")
    print("="*70)
    
    check_bounce_rate()
    check_top_pages()
    check_product_views()
    check_event_distribution()
    
    print("="*70)
    print("✅ Metrics check complete!")
    print("="*70)
    print()

if __name__ == "__main__":
    main()
