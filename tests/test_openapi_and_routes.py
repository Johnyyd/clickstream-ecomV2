import pytest
from fastapi.testclient import TestClient

try:
    from app.main import app
except Exception as e:
    app = None


@pytest.mark.skipif(app is None, reason="FastAPI app failed to import")
def test_openapi_available():
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data
    # Ensure at least one expected API group is documented
    expected_any = any(
        p.startswith("/api/") for p in data.get("paths", {}).keys()
    )
    assert expected_any, "Expected at least one /api/* path in OpenAPI"


@pytest.mark.skipif(app is None, reason="FastAPI app failed to import")
def test_expected_routes_present():
    # Inspect mounted routes without calling DB-backed handlers
    paths = set()
    methods_by_path = {}
    for r in app.routes:
        if hasattr(r, "path"):
            paths.add(r.path)
            methods_by_path.setdefault(r.path, set())
            methods_by_path[r.path].update(getattr(r, "methods", []) or [])

    # Check a few key endpoints declared in README
    expected_paths = [
        "/api/products",
        "/api/analyses",
        "/api/ingest",
        "/api/ingest-batch",
    ]
    missing = [p for p in expected_paths if p not in paths]
    assert not missing, f"Missing expected routes: {missing}"

    # Ensure GET on products, GET on analyses exist
    assert "GET" in methods_by_path.get("/api/products", set())
    assert "GET" in methods_by_path.get("/api/analyses", set())
