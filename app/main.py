from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from app.api import events as events_api
from app.api import analyses as analyses_api
from app.api import auth as auth_api
from app.api import products as products_api
from app.api import analysis as analysis_api
from app.api import openrouter as openrouter_api
from app.api import recommendations as recommendations_api
from app.api import metrics as metrics_api
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi import Request
from fastapi.responses import Response
from app.repositories.indexes import ensure_indexes

app = FastAPI(title="Clickstream Ecom V2 API", version="0.1.0")

# Basic CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok", "engine": os.environ.get("ANALYSIS_ENGINE", "python")}

@app.on_event("startup")
def _on_startup():
    try:
        ensure_indexes()
    except Exception:
        # Avoid crashing app if index creation fails in initial boot
        pass

# Placeholder root for sanity check
@app.get("/")
def root():
    # Serve storefront home by default
    static_dir = Path(__file__).resolve().parent.parent / "static"
    index_path = static_dir / "home.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return JSONResponse({"message": "Clickstream-ecomV2 FastAPI is running"})

# Static files mount
static_path = Path(__file__).resolve().parent.parent / "static"
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

# Routers
app.include_router(events_api.router)
app.include_router(analyses_api.router)
app.include_router(auth_api.router)
app.include_router(products_api.router)
app.include_router(analysis_api.router)
app.include_router(openrouter_api.router)
app.include_router(recommendations_api.router)
app.include_router(metrics_api.router)
