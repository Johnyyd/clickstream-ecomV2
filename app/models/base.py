"""
Base Models for API
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class EventBase(TimestampMixin):
    """Base model for clickstream events"""
    user_id: str
    session_id: str
    event_type: str
    page: str
    timestamp: int
    properties: Dict[str, Any] = Field(default_factory=dict)

class SessionBase(TimestampMixin):
    """Base model for user sessions"""
    session_id: str
    user_id: str
    first_event_at: datetime
    last_event_at: datetime
    event_count: int = 0
    pages: List[str] = Field(default_factory=list)

class ProductBase(TimestampMixin):
    """Base model for products"""
    name: str
    category: str
    price: float
    description: Optional[str] = None
    image_url: Optional[str] = None
    slug: Optional[str] = None

class UserBase(TimestampMixin):
    """Base model for users"""
    username: str
    email: str
    is_active: bool = True
    is_superuser: bool = False

class AnalysisBase(TimestampMixin):
    """Base model for analysis results"""
    analysis_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CartBase(TimestampMixin):
    """Base model for shopping carts"""
    user_id: str
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: float = 0.0

class APIResponse(BaseModel):
    """Standard API response model"""
    status: str = "success"
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None

# Request Models
class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str

class RegisterRequest(BaseModel):
    """Registration request model"""
    username: str
    email: str
    password: str

class AnalysisRequest(BaseModel):
    """Analysis request model"""
    analysis_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)