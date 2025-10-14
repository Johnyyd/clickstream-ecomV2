from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from db import products_col
from .models import Product, PaginatedProducts

class ProductsRepository:
    def __init__(self) -> None:
        self._col = products_col()

    def _clean(self, doc: Dict[str, Any]) -> Product:
        if not doc:
            return Product()
        doc = dict(doc)
        doc["_id"] = str(doc.get("_id")) if doc.get("_id") is not None else None
        if not doc.get("image_url"):
            doc["image_url"] = "/static/images/placeholder.svg"
        return Product.model_validate(doc)

    def list(
        self,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        tags: Optional[List[str]] = None,
        limit: int = 12,
        offset: int = 0,
        sort: Optional[Tuple[str, int]] = None,
    ) -> PaginatedProducts:
        q: Dict[str, Any] = {}
        if category:
            q["category"] = category
        price: Dict[str, Any] = {}
        if min_price is not None:
            price["$gte"] = float(min_price)
        if max_price is not None:
            price["$lte"] = float(max_price)
        if price:
            q["price"] = price
        if tags:
            q["tags"] = {"$in": tags}

        cur = self._col.find(q)
        if sort:
            cur = cur.sort([sort])
        try:
            total = self._col.count_documents(q)
        except Exception:
            total = 0
        docs = list(cur.skip(offset).limit(limit))
        items = [self._clean(d) for d in docs]
        return PaginatedProducts(items=items, total=total, limit=limit, offset=offset)

    def get_by_id(self, pid: str) -> Optional[Product]:
        try:
            doc = self._col.find_one({"_id": ObjectId(pid)})
        except Exception:
            doc = None
        if not doc:
            return None
        return self._clean(doc)

    def get_by_slug(self, slug: str) -> Optional[Product]:
        doc = self._col.find_one({"slug": slug})
        if not doc:
            return None
        return self._clean(doc)

    def categories(self) -> List[str]:
        cats = self._col.distinct("category")
        return sorted([c for c in cats if isinstance(c, str)])

    def search(
        self,
        q: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        tags: Optional[List[str]] = None,
        limit: int = 12,
        offset: int = 0,
        sort: Optional[Tuple[str, int]] = None,
    ) -> PaginatedProducts:
        filter_q: Dict[str, Any] = {}
        if q:
            filter_q = {"$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"category": {"$regex": q, "$options": "i"}},
                {"tags": {"$elemMatch": {"$regex": q, "$options": "i"}}},
            ]}
        price: Dict[str, Any] = {}
        if min_price is not None:
            price["$gte"] = float(min_price)
        if max_price is not None:
            price["$lte"] = float(max_price)
        if price:
            filter_q["price"] = price
        if tags:
            filter_q["tags"] = {"$in": tags}

        cur = self._col.find(filter_q)
        if sort:
            cur = cur.sort([sort])
        try:
            total = self._col.count_documents(filter_q)
        except Exception:
            total = 0
        docs = list(cur.skip(offset).limit(limit))
        items = [self._clean(d) for d in docs]
        return PaginatedProducts(items=items, total=total, limit=limit, offset=offset)
