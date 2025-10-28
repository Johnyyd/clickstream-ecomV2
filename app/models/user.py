"""
User models
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import pytz

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_active: bool = True
    is_admin: bool = False

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class User(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime = Field(default_factory=datetime.now(pytz.UTC))

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }