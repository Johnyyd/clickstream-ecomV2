from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class Product(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    slug: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[Any] = None

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True

class PaginatedProducts(BaseModel):
    items: List[Product]
    total: int
    limit: int
    offset: int
