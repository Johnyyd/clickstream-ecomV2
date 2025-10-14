from fastapi import APIRouter, Query
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

@router.get("/categories")
def list_categories():
    repo = ProductsRepository()
    cats = repo.categories()
    return {"items": cats}

@router.get("/product/{pid}")
def get_product(pid: str):
    repo = ProductsRepository()
    prod = repo.get_by_id(pid)
    if not prod:
        return {"error": "not found"}
    return prod.model_dump(by_alias=True)

@router.get("/product/slug/{slug}")
def get_product_by_slug(slug: str):
    repo = ProductsRepository()
    prod = repo.get_by_slug(slug)
    if not prod:
        return {"error": "not found"}
    return prod.model_dump(by_alias=True)

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
