from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from auth import create_user, login_user

router = APIRouter(prefix="/api", tags=["auth"])

class SignUpBody(BaseModel):
    username: str
    email: str
    password: str

class LoginBody(BaseModel):
    username: str
    password: str

@router.post("/signup")
def signup(body: SignUpBody):
    uid = create_user(body.username, body.email, body.password)
    return {"user_id": str(uid)}

@router.post("/login")
def login(body: LoginBody):
    result, msg = login_user(body.username, body.password)
    if not result:
        return {"error": msg}
    return {
        "token": result["token"],
        "user_id": str(result["user"]["_id"]),
        "username": result["user"].get("username")
    }
