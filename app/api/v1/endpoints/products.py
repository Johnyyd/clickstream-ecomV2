"""
Products API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.core.db_sync import events_col, sessions_col, products_col, users_col, carts_col
from app.models.product import Product, ProductCreate, ProductUpdate
from ..deps import get_db, get_current_user
from ..models import ProductResponse

router = APIRouter()

@router.get("/", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    db = Depends(get_db)
):
    """
    List products with optional filtering
    """
    products = await db.products.get_all(skip=skip, limit=limit, category=category)
    return products

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db = Depends(get_db)
):
    """
    Get single product by ID
    """
    product = await db.products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create new product (admin only)
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    return await db.products.create(product)

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product: ProductUpdate,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update product (admin only)
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    updated = await db.products.update(product_id, product)
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated

@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete product (admin only)
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    success = await db.products.delete(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}