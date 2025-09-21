# test_product_interactions.py - Test product interactions and user behavior patterns
from analysis import run_analysis
from db import events_col, users_col, products_col, analyses_col
from bson import ObjectId
import json
from collections import Counter, defaultdict

def analyze_product_interactions():
    """Analyze how users interact with products"""
    print("🛍️ Analyzing Product Interactions...")
    
    # Get all events
    events = list(events_col().find())
    users = list(users_col().find())
    products = list(products_col().find())
    
    print(f"📊 Data Overview:")
    print(f"  • Total Events: {len(events)}")
    print(f"  • Total Users: {len(users)}")
    print(f"  • Total Products: {len(products)}")
    
    # Analyze product views
    product_views = []
    product_purchases = []
    user_product_interactions = defaultdict(list)
    
    for event in events:
        user_id = event.get('user_id')
        properties = event.get('properties', {})
        
        if event.get('event_type') == 'pageview' and properties.get('product_id'):
            product_views.append({
                'user_id': user_id,
                'product_id': properties.get('product_id'),
                'product_name': properties.get('product_name'),
                'product_category': properties.get('product_category'),
                'product_price': properties.get('product_price'),
                'timestamp': event.get('timestamp')
            })
            user_product_interactions[user_id].append(properties.get('product_id'))
            
        elif event.get('event_type') == 'add_to_cart' and properties.get('product_id'):
            product_purchases.append({
                'user_id': user_id,
                'product_id': properties.get('product_id'),
                'product_name': properties.get('product_name'),
                'product_price': properties.get('product_price'),
                'timestamp': event.get('timestamp')
            })
    
    print(f"\n📈 Product Interaction Statistics:")
    print(f"  • Product Views: {len(product_views)}")
    print(f"  • Add to Cart: {len(product_purchases)}")
    print(f"  • Users with Product Interactions: {len(user_product_interactions)}")
    
    # Most viewed products
    product_view_counts = Counter([pv['product_id'] for pv in product_views])
    print(f"\n🔥 Most Viewed Products:")
    for product_id, count in product_view_counts.most_common(5):
        product = next((p for p in products if str(p['_id']) == product_id), None)
        if product:
            print(f"  • {product['name']} ({product['category']}): {count} views")
    
    # Most purchased products
    product_purchase_counts = Counter([pp['product_id'] for pp in product_purchases])
    print(f"\n💰 Most Purchased Products:")
    for product_id, count in product_purchase_counts.most_common(5):
        product = next((p for p in products if str(p['_id']) == product_id), None)
        if product:
            print(f"  • {product['name']} ({product['category']}): {count} purchases")
    
    # User behavior patterns
    print(f"\n👥 User Behavior Patterns:")
    for user in users:
        user_id = user['_id']
        user_interactions = user_product_interactions.get(user_id, [])
        
        if user_interactions:
            unique_products = len(set(user_interactions))
            total_views = len(user_interactions)
            
            print(f"  • {user['username']} ({user['profile']['user_type']}):")
            print(f"    - Viewed {unique_products} unique products")
            print(f"    - Total product views: {total_views}")
            print(f"    - Preferred categories: {user['profile']['interests']}")
    
    return product_views, product_purchases, user_product_interactions

def create_user_product_profiles():
    """Create detailed user-product interaction profiles"""
    print("\n👤 Creating User-Product Profiles...")
    
    users = list(users_col().find())
    products = list(products_col().find())
    events = list(events_col().find())
    
    user_profiles = {}
    
    for user in users:
        user_id = user['_id']
        user_events = [e for e in events if e.get('user_id') == user_id]
        
        # Analyze user's product interactions
        product_views = []
        product_purchases = []
        categories_viewed = set()
        brands_viewed = set()
        price_range = {'min': float('inf'), 'max': 0}
        
        for event in user_events:
            properties = event.get('properties', {})
            
            if event.get('event_type') == 'pageview' and properties.get('product_id'):
                product_views.append(properties)
                categories_viewed.add(properties.get('product_category', ''))
                brands_viewed.add(properties.get('product_brand', ''))
                
                price = properties.get('product_price', 0)
                if price:
                    price_range['min'] = min(price_range['min'], price)
                    price_range['max'] = max(price_range['max'], price)
                    
            elif event.get('event_type') == 'add_to_cart' and properties.get('product_id'):
                product_purchases.append(properties)
        
        # Calculate user preferences
        category_preferences = Counter([pv.get('product_category', '') for pv in product_views])
        brand_preferences = Counter([pv.get('product_brand', '') for pv in product_views])
        
        user_profiles[user_id] = {
            'user_info': {
                'username': user['username'],
                'user_type': user['profile']['user_type'],
                'age_group': user['profile']['age_group'],
                'interests': user['profile']['interests']
            },
            'interaction_stats': {
                'total_product_views': len(product_views),
                'unique_products_viewed': len(set(pv.get('product_id') for pv in product_views)),
                'total_purchases': len(product_purchases),
                'categories_viewed': list(categories_viewed),
                'brands_viewed': list(brands_viewed),
                'price_range': price_range if price_range['min'] != float('inf') else {'min': 0, 'max': 0}
            },
            'preferences': {
                'top_categories': [cat for cat, count in category_preferences.most_common(3)],
                'top_brands': [brand for brand, count in brand_preferences.most_common(3)],
                'avg_product_price': sum(pv.get('product_price', 0) for pv in product_views) / len(product_views) if product_views else 0
            },
            'behavior_patterns': {
                'session_count': len(set(e.get('session_id') for e in user_events)),
                'avg_events_per_session': len(user_events) / len(set(e.get('session_id') for e in user_events)) if user_events else 0,
                'conversion_rate': len(product_purchases) / len(product_views) if product_views else 0
            }
        }
    
    # Display user profiles
    for user_id, profile in user_profiles.items():
        print(f"\n👤 {profile['user_info']['username']} ({profile['user_info']['user_type']})")
        print(f"   Age Group: {profile['user_info']['age_group']}")
        print(f"   Interests: {', '.join(profile['user_info']['interests'])}")
        print(f"   Product Views: {profile['interaction_stats']['total_product_views']}")
        print(f"   Unique Products: {profile['interaction_stats']['unique_products_viewed']}")
        print(f"   Purchases: {profile['interaction_stats']['total_purchases']}")
        print(f"   Top Categories: {', '.join(profile['preferences']['top_categories'])}")
        print(f"   Top Brands: {', '.join(profile['preferences']['top_brands'])}")
        print(f"   Avg Price: ${profile['preferences']['avg_product_price']:.2f}")
        print(f"   Conversion Rate: {profile['behavior_patterns']['conversion_rate']:.1%}")
    
    return user_profiles

def test_analysis_with_product_data():
    """Test analysis with the new product-focused data"""
    print("\n🔍 Testing Analysis with Product Data...")
    
    # Get a user for analysis
    users = list(users_col().find())
    if not users:
        print("❌ No users found for analysis")
        return
    
    user = users[0]
    print(f"Running analysis for user: {user['username']} ({user['_id']})")
    
    try:
        # Run analysis
        analysis_result = run_analysis(str(user['_id']), {"limit": 1000})
        
        # Get saved analysis
        saved_analysis = analyses_col().find_one({"_id": analysis_result["_id"]})
        
        if saved_analysis:
            print("✅ Analysis completed successfully")
            
            # Show detailed metrics
            detailed_metrics = saved_analysis.get("detailed_metrics", {})
            basic_metrics = detailed_metrics.get("basic_metrics", {})
            
            print(f"\n📊 Analysis Results:")
            print(f"  • Total Events: {basic_metrics.get('total_events', 0)}")
            print(f"  • Total Sessions: {basic_metrics.get('total_sessions', 0)}")
            print(f"  • Unique Users: {basic_metrics.get('unique_users', 0)}")
            print(f"  • Bounce Rate: {basic_metrics.get('bounce_rate', 0):.1%}")
            print(f"  • Avg Session Duration: {basic_metrics.get('avg_session_duration_seconds', 0)/60:.1f} minutes")
            
            # Show page analysis
            page_analysis = detailed_metrics.get("page_analysis", {})
            top_pages = page_analysis.get("top_pages", [])
            print(f"\n📄 Top Pages:")
            for page in top_pages[:5]:
                print(f"  • {page['page']}: {page['count']} views")
            
            # Show funnel analysis
            funnel_analysis = detailed_metrics.get("funnel_analysis", {})
            print(f"\n🔄 Funnel Analysis:")
            for funnel_name, funnel_data in funnel_analysis.items():
                if funnel_data.get("conversion", 0) > 0:
                    print(f"  • {funnel_name}: {funnel_data['conversion']:.1%} conversion")
            
            # Show insights
            insights = saved_analysis.get("insights", {})
            if insights.get("key_findings"):
                print(f"\n💡 Key Insights:")
                for finding in insights["key_findings"][:3]:
                    print(f"  • {finding}")
            
            if insights.get("recommendations"):
                print(f"\n💡 Recommendations:")
                for rec in insights["recommendations"][:3]:
                    print(f"  • {rec}")
        
        else:
            print("❌ Analysis not found in database")
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

def create_product_analytics_report():
    """Create a comprehensive product analytics report"""
    print("\n📈 Creating Product Analytics Report...")
    
    events = list(events_col().find())
    products = list(products_col().find())
    
    # Product performance metrics
    product_metrics = {}
    
    for product in products:
        product_id = str(product['_id'])
        product_events = [e for e in events if e.get('properties', {}).get('product_id') == product_id]
        
        views = len([e for e in product_events if e.get('event_type') == 'pageview'])
        purchases = len([e for e in product_events if e.get('event_type') == 'add_to_cart'])
        
        product_metrics[product_id] = {
            'name': product['name'],
            'category': product['category'],
            'price': product['price'],
            'views': views,
            'purchases': purchases,
            'conversion_rate': purchases / views if views > 0 else 0,
            'revenue': purchases * product['price']
        }
    
    # Sort by different metrics
    by_views = sorted(product_metrics.values(), key=lambda x: x['views'], reverse=True)
    by_purchases = sorted(product_metrics.values(), key=lambda x: x['purchases'], reverse=True)
    by_conversion = sorted(product_metrics.values(), key=lambda x: x['conversion_rate'], reverse=True)
    by_revenue = sorted(product_metrics.values(), key=lambda x: x['revenue'], reverse=True)
    
    print(f"\n🏆 Product Performance Report:")
    
    print(f"\n📊 Top Products by Views:")
    for product in by_views[:5]:
        print(f"  • {product['name']} ({product['category']}): {product['views']} views")
    
    print(f"\n💰 Top Products by Purchases:")
    for product in by_purchases[:5]:
        print(f"  • {product['name']} ({product['category']}): {product['purchases']} purchases")
    
    print(f"\n🎯 Top Products by Conversion Rate:")
    for product in by_conversion[:5]:
        if product['conversion_rate'] > 0:
            print(f"  • {product['name']} ({product['category']}): {product['conversion_rate']:.1%} conversion")
    
    print(f"\n💵 Top Products by Revenue:")
    for product in by_revenue[:5]:
        print(f"  • {product['name']} ({product['category']}): ${product['revenue']:.2f} revenue")
    
    # Category analysis
    category_metrics = defaultdict(lambda: {'views': 0, 'purchases': 0, 'revenue': 0})
    
    for product in product_metrics.values():
        category = product['category']
        category_metrics[category]['views'] += product['views']
        category_metrics[category]['purchases'] += product['purchases']
        category_metrics[category]['revenue'] += product['revenue']
    
    print(f"\n📂 Category Performance:")
    for category, metrics in category_metrics.items():
        conversion_rate = metrics['purchases'] / metrics['views'] if metrics['views'] > 0 else 0
        print(f"  • {category}: {metrics['views']} views, {metrics['purchases']} purchases, {conversion_rate:.1%} conversion, ${metrics['revenue']:.2f} revenue")

def main():
    """Main function to test product interactions"""
    print("🛍️ Product Interaction Analysis")
    print("=" * 50)
    
    # 1. Analyze product interactions
    product_views, product_purchases, user_interactions = analyze_product_interactions()
    
    # 2. Create user-product profiles
    user_profiles = create_user_product_profiles()
    
    # 3. Test analysis with product data
    test_analysis_with_product_data()
    
    # 4. Create product analytics report
    create_product_analytics_report()
    
    print(f"\n🎉 Product interaction analysis completed!")
    print(f"   The system now has:")
    print(f"   • Consistent ID management")
    print(f"   • Realistic user-product interactions")
    print(f"   • Detailed product analytics")
    print(f"   • User behavior profiling")
    print(f"   • Comprehensive analysis capabilities")

if __name__ == "__main__":
    main()
