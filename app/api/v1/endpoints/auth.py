"""
Authentication API endpoints
Provides both session-based and JWT token-based authentication
"""
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from app.models.user import UserInDB

from app.core.config import settings
from app.services.auth import (
    authenticate_user_async,
    create_access_token,
    create_user,
    login_user,
    get_user_by_token
)
from ..deps import get_db
from ..models import Token

router = APIRouter()

# Models
class SignUpBody(BaseModel):
    username: str
    email: str
    password: str

class LoginBody(BaseModel):
    username: str
    password: str

@router.post("/signup")
async def signup(body: SignUpBody):
    """Create a new user account"""
    result = create_user(body.username, body.email, body.password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/login")
def login(body: LoginBody):
    """Login with username/password for session token"""
    result = login_user(body.username, body.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    return result

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_db)
):
    """OAuth2 compatible token login for JWT token"""
    user = await authenticate_user_async(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserInDB)
async def register_new_user(
    user_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_db)
):
    """
    Register a new user
    """
    existing_user = await db.users.get_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
        
    user = await db.users.create(user_data.username, user_data.password)
    return user