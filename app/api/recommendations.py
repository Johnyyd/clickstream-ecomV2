from fastapi import APIRouter, Header, Body
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.services.auth import get_user_by_token
from app.core.db_sync import users_col, analyses_col, products_col
from collections import Counter

router = APIRouter(tags=["recommendations"])  # Prefix set in main.py

def calculate_session_score(product: Dict[str, Any], session_context: Dict[str, Any]) -> float:
    """
    Calculate relevance score based on session context.
    Higher score = more relevant to current session.
    """
    score = 0.0
    
    # Extract session data
    cart_ids = set(session_context.get("cart_product_ids", []))
    viewed_ids = set(session_context.get("viewed_product_ids", []))
    
    # Get categories and tags from session products
    session_categories = session_context.get("categories", [])
    session_tags = session_context.get("tags", [])
    
    product_id = str(product.get("_id", ""))
    product_category = product.get("category", "")
    product_tags = product.get("tags", [])
    
    # Don't recommend products already in cart
    if product_id in cart_ids:
        return -1000.0
    
    # Reduce score for already viewed products
    if product_id in viewed_ids:
        score -= 2.0
    
    # Category matching (strong signal)
    if product_category and product_category in session_categories:
        category_count = session_categories.count(product_category)
        score += 5.0 * category_count
    
    # Tag matching (moderate signal)
    if product_tags and session_tags:
        matching_tags = set(product_tags) & set(session_tags)
        score += 2.0 * len(matching_tags)
    
    return score

@router.post("/recommendations")
def get_recommendations_with_context(
    session_context: Dict[str, Any] = Body(default={}),
    Authorization: Optional[str] = Header(default=None),
    limit: int = 12,
    offset: int = 0
):
    """
    Get recommendations with session context for real-time personalization.
    
    session_context should include:
    - cart_product_ids: List of product IDs in cart
    - viewed_product_ids: List of recently viewed product IDs
    - categories: List of categories from session products
    - tags: List of tags from session products
    """
    if not Authorization:
        return {"error": "unauthenticated"}
    user = get_user_by_token(Authorization)
    if not user:
        return {"error": "unauthenticated"}

    try:
        # Get base recommendations from pre-computed data
        last = analyses_col().find({
            "user_id": user["_id"],
            "product_recommendations": {"$exists": True, "$ne": []}
        }).sort("created_at", -1).limit(1)
        last = list(last)
        base_items: List[Dict[str, Any]] = []
        if last:
            base_items = last[0].get("product_recommendations", [])
        if not base_items:
            udoc = users_col().find_one({"_id": user["_id"]}, {"product_recommendations": 1}) or {}
            history = udoc.get("product_recommendations", [])
            if history:
                base_items = (history[-1] or {}).get("items", [])

        # Get product IDs from base recommendations
        base_product_ids = [i.get("product_id") for i in base_items if i.get("product_id")]
        
        # Fetch full product data
        obj_ids = []
        for pid in base_product_ids:
            try:
                obj_ids.append(ObjectId(str(pid)))
            except Exception:
                pass
        
        products = []
        if obj_ids:
            products = list(products_col().find({"_id": {"$in": obj_ids}}))
        
        # If no base recommendations or session context provided, use category/tag based recommendations
        if not products or session_context:
            # Get additional products based on session context
            session_categories = session_context.get("categories", [])
            session_tags = session_context.get("tags", [])
            cart_ids = session_context.get("cart_product_ids", [])
            
            additional_filter = {}
            if session_categories or session_tags:
                additional_filter["$or"] = []
                if session_categories:
                    additional_filter["$or"].append({"category": {"$in": session_categories}})
                if session_tags:
                    additional_filter["$or"].append({"tags": {"$in": session_tags}})
                
                # Exclude cart items
                if cart_ids:
                    try:
                        cart_obj_ids = [ObjectId(str(pid)) for pid in cart_ids if pid]
                        additional_filter["_id"] = {"$nin": cart_obj_ids}
                    except:
                        pass
                
                # Get up to 50 products matching session context
                context_products = list(products_col().find(additional_filter).limit(50))
                
                # Merge with base products (deduplicate)
                existing_ids = {str(p["_id"]) for p in products}
                for p in context_products:
                    if str(p["_id"]) not in existing_ids:
                        products.append(p)
        
        # Calculate session scores for all products
        if session_context:
            scored_products = []
            for p in products:
                score = calculate_session_score(p, session_context)
                if score > -100:  # Filter out products in cart
                    scored_products.append((p, score))
            
            # Sort by score (descending)
            scored_products.sort(key=lambda x: x[1], reverse=True)
            products = [p for p, score in scored_products]
        
        # Build result items
        result_items = []
        for p in products:
            result_items.append({
                "product_id": str(p["_id"]),
                "name": p.get("name"),
                "category": p.get("category"),
                "price": p.get("price"),
                "image_url": p.get("image_url"),
                "tags": p.get("tags", []),
                "reason": "Based on your current session"
            })
        
        # Paginate
        total = len(result_items)
        paginated = result_items[offset : offset + limit]
        return {"items": paginated, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@router.get("/recommendations")
def get_recommendations(
    Authorization: Optional[str] = Header(default=None),
    limit: int = 12,
    offset: int = 0
):
    """Legacy GET endpoint for backward compatibility"""
    return get_recommendations_with_context(
        session_context={},
        Authorization=Authorization,
        limit=limit,
        offset=offset
    )
