from fastapi import FastAPI, HTTPException, status, Request
from fastapi import Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from pydantic import BaseModel

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import setup_error_handlers
from app.core.logging import setup_logging
from app.repositories.indexes import ensure_indexes
from app.services.auth import login_user, create_user

# Import routers
from app.api import (
    events as events_api,
    analyses as analyses_api,
    auth as auth_api,
    products as products_api,
    analysis as analysis_api,
    openrouter as openrouter_api,
    recommendations as recommendations_api,
    metrics as metrics_api,
    cart as cart_api,
    ml as ml_api,
    analytics_comprehensive as analytics_comprehensive_api
)

# Setup logging
logger = setup_logging(
    level=settings.LOG_LEVEL,
    log_file=Path("logs/app.log") if settings.LOG_TO_FILE else None
)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Setup error handlers
setup_error_handlers(app)

# Health check endpoint
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "engine": settings.ANALYSIS_ENGINE
    }

# Test endpoint to check user in database
@app.get("/api/test-user/{username}")
def test_user(username: str):
    """Debug endpoint to check user data"""
    from app.repositories.users_repo import UsersRepository
    repo = UsersRepository()
    user = repo.find_by_username(username)
    if not user:
        return {"error": "User not found"}
    # Return user info (except password)
    return {
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "has_password_hash": "password_hash" in user,
        "has_hashed_password": "hashed_password" in user,
        "has_password": "password" in user,
        "_id": str(user.get("_id"))
    }

# Get current user info from token
@app.get("/api/me")
def get_me(Authorization: Optional[str] = Header(default=None)):
    """Get current user info from token. Avoids raising to prevent 500s in UI flows."""
    try:
        from app.services.auth import get_user_by_token
        if not Authorization:
            return {"error": "unauthenticated"}

        user = get_user_by_token(Authorization)
        if not user:
            return {"error": "unauthenticated"}

        uid = user.get("_id")
        try:
            uid_str = str(uid)
        except Exception:
            uid_str = None

        return {
            "user_id": uid_str,
            "id": uid_str,
            "_id": uid_str,
            "username": user.get("username"),
            "email": user.get("email"),
            "role": user.get("role", "user")
        }
    except Exception as e:
        # Last-resort guard to avoid 500 to the dashboard
        return {"error": "INTERNAL_ERROR", "message": str(e)}

# Auth models
class LoginBody(BaseModel):
    username: str
    password: str

class SignUpBody(BaseModel):
    username: str
    email: str
    password: str

# Direct auth endpoints for backward compatibility
@app.post("/api/login")
def direct_login(body: LoginBody):
    """Direct login endpoint - backward compatibility"""
    result = login_user(body.username, body.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    return result

@app.post("/api/signup")
def direct_signup(body: SignUpBody):
    """Direct signup endpoint - backward compatibility"""
    result = create_user(body.username, body.email, body.password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.on_event("startup")
async def startup():
    """
    Startup tasks
    """
    try:
        # Create MongoDB indexes
        ensure_indexes()
        logger.info("Successfully created MongoDB indexes")
    except Exception as e:
        logger.error(f"Failed to create indexes: {str(e)}")

# Mount API routes
app.include_router(api_router)

# Ensure versioned mounts exist explicitly for critical groups
try:
    app.include_router(metrics_api.router, prefix="/api/v1/metrics")
    app.include_router(cart_api.router, prefix="/api/v1/cart")
    app.include_router(analytics_comprehensive_api.router, prefix="/api/v1/analytics")
    app.include_router(recommendations_api.router, prefix="/api/v1/recommendations")
    app.include_router(products_api.router, prefix="/api/v1/products")
    app.include_router(analysis_api.router, prefix="/api/v1/analyses")
    app.include_router(ml_api.router, prefix="/api/v1/ml")
    app.include_router(auth_api.router, prefix="/api/v1/auth")
    app.include_router(events_api.router, prefix="/api/v1/events")
except Exception:
    # Best-effort: if any alias import missing, skip
    pass

# Serve static files
static_path = Path(__file__).parent.parent / "static"

@app.get("/")
async def root():
    """
    Serve root endpoint
    """
    index_path = static_path / "auth.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return JSONResponse({"message": "Clickstream-ecomV2 FastAPI is running"})

# Mount static files
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Pretty routes mapping
_pretty_routes = {
    "/home": "home.html",
    "/category": "category.html",
    "/search": "search.html",
    "/product": "product.html",
    "/cart": "cart.html",
    "/checkout": "checkout.html",
    "/dashboard": "index.html",
    "/dashboard-spa": "spa/index.html",
    "/auth": "auth.html",
}

def _serve_static_file(filename: str):
    path = static_path / filename
    if path.exists():
        # Infer basic content type
        if filename.endswith(".html"):
            return FileResponse(str(path), media_type="text/html")
        if filename.endswith(".css"):
            return FileResponse(str(path), media_type="text/css")
        if filename.endswith(".js"):
            return FileResponse(str(path), media_type="application/javascript")
        return FileResponse(str(path))
    return JSONResponse({"error": "not found"}, status_code=404)

for route, fname in _pretty_routes.items():
    app.add_api_route(route, lambda f=fname: _serve_static_file(f), methods=["GET"])  # type: ignore

# Support dynamic product path /product/<id> by serving product.html
@app.get("/product/{pid}")
def _product_dynamic(pid: str):  # noqa: ARG001
    return _serve_static_file("product.html")

# Support pretty slug path /p/<slug> by serving product.html
@app.get("/p/{slug}")
def _product_slug(slug: str):  # noqa: ARG001
    return _serve_static_file("product.html")
