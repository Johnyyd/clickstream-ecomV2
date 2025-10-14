from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from app.repositories.products_repo import ProductsRepository

router = APIRouter(prefix="/api", tags=["products"])

@router.get("/products")
def list_products(
    category: Optional[str] = None,
    min_price: Optional[float] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    tags: Optional[str] = None,
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Optional[str] = None,
):
    repo = ProductsRepository()
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    sort_spec = None
    if sort == "price_asc":
        sort_spec = ("price", 1)
    elif sort == "price_desc":
        sort_spec = ("price", -1)
    elif sort == "name_asc":
        sort_spec = ("name", 1)
    elif sort == "name_desc":
        sort_spec = ("name", -1)
    elif sort == "created_desc":
        sort_spec = ("created_at", -1)
    try:
        page = repo.list(
            category=category,
            min_price=min_price,
            max_price=max_price,
            tags=tag_list,
            limit=limit,
            offset=offset,
            sort=sort_spec,
        )
        return page.model_dump(by_alias=True)
    except Exception as e:
        # If DB is not reachable, surface a 500 for smoke tests to accept
        raise HTTPException(status_code=500, detail="Database unavailable")

@router.get("/categories")
def list_categories():
    repo = ProductsRepository()
    try:
        cats = repo.categories()
        return {"items": cats}
    except Exception:
        raise HTTPException(status_code=500, detail="Database unavailable")

@router.get("/product/{pid}")
def get_product(pid: str):
    repo = ProductsRepository()
    try:
        prod = repo.get_by_id(pid)
        if not prod:
            return {"error": "not found"}
        return prod.model_dump(by_alias=True)
    except Exception:
        raise HTTPException(status_code=500, detail="Database unavailable")

@router.get("/product/slug/{slug}")
def get_product_by_slug(slug: str):
    repo = ProductsRepository()
    try:
        prod = repo.get_by_slug(slug)
        if not prod:
            return {"error": "not found"}
        return prod.model_dump(by_alias=True)
    except Exception:
        raise HTTPException(status_code=500, detail="Database unavailable")

@router.get("/search")
def search_products(
    q: Optional[str] = Query(default=None),
    min_price: Optional[float] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    tags: Optional[str] = None,
    limit: int = Query(default=12, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: Optional[str] = None,
):
    repo = ProductsRepository()
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    sort_spec = None
    if sort == "price_asc":
        sort_spec = ("price", 1)
    elif sort == "price_desc":
        sort_spec = ("price", -1)
    elif sort == "name_asc":
        sort_spec = ("name", 1)
    elif sort == "name_desc":
        sort_spec = ("name", -1)
    elif sort == "created_desc":
        sort_spec = ("created_at", -1)
    try:
        page = repo.search(
            q=q,
            min_price=min_price,
            max_price=max_price,
            tags=tag_list,
            limit=limit,
            offset=offset,
            sort=sort_spec,
        )
        return page.model_dump(by_alias=True)
    except Exception:
        raise HTTPException(status_code=500, detail="Database unavailable")
