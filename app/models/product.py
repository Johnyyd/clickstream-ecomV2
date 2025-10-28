"""
Product models for the e-commerce system
Includes base model and specialized versions for create/update/response
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class ProductBase(BaseModel):
    """Base product attributes shared by all product models"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    
    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price cannot be negative")
        return round(v, 2)  # Round to 2 decimal places

class ProductCreate(ProductBase):
    """Model for creating new products"""
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProductUpdate(ProductBase):
    """Model for updating existing products"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class Product(ProductBase):
    """Complete product model with database fields"""
    id: str
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    views_count: int = Field(default=0, ge=0)
    purchases_count: int = Field(default=0, ge=0)

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }
        from_attributes = True
    pass

class ProductUpdate(ProductBase):
    pass

class ProductInDB(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True