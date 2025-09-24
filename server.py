# server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, urllib
from urllib.parse import urlparse, parse_qs
from ingest import ingest_event
from auth import create_user, create_session, get_user_by_token, verify_password, hash_password
from analysis import run_analysis
from db import users_col, analyses_col, api_keys_col, products_col
from bson import ObjectId
from datetime import datetime

PORT = int(os.environ.get("PORT", 8000))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

def read_json(rfile, length):
    data = rfile.read(length).decode("utf-8")
    return json.loads(data) if data else {}

class SimpleHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type,Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        # Map pretty storefront routes to static HTML files
        pretty_routes = {
            "/home": "home.html",
            "/category": "category.html",
            "/search": "search.html",
            "/product": "product.html",
            "/cart": "cart.html",
            "/checkout": "checkout.html",
        }
        if path in pretty_routes:
            file_path = os.path.join(STATIC_DIR, pretty_routes[path])
            if os.path.exists(file_path):
                self._set_headers(200, content_type="text/html")
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self._set_headers(404)
                self.wfile.write(b'{"error":"not found"}')
                return

        # Serve static assets under /static/* including images
        # Pretty product URL: /p/<slug> should serve product.html
        if path.startswith("/p/"):
            try:
                file_path = os.path.join(STATIC_DIR, "product.html")
                self._set_headers(200, content_type="text/html")
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            except Exception:
                pass
        if path == "/" or path.startswith("/static/") or path.endswith((".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg")) or path == "/dashboard":
            try:
                if path == "/":
                    # Default storefront home
                    file_path = os.path.join(STATIC_DIR, "home.html")
                elif path == "/dashboard":
                    # Legacy dashboard
                    file_path = os.path.join(STATIC_DIR, "index.html")
                else:
                    rel = path.lstrip("/")
                    # allow both /static/foo and /foo to map inside STATIC_DIR
                    if rel.startswith("static/"):
                        rel = rel[len("static/"):]
                    file_path = os.path.join(STATIC_DIR, rel)

                file_path = os.path.normpath(file_path)
                if not file_path.startswith(STATIC_DIR):
                    self._set_headers(403)
                    self.wfile.write(b'{"error":"forbidden"}')
                    return

                if os.path.exists(file_path):
                    ctype = "application/octet-stream"
                    if file_path.endswith(".html"):
                        ctype = "text/html"
                    elif file_path.endswith(".css"):
                        ctype = "text/css"
                    elif file_path.endswith(".js"):
                        ctype = "application/javascript"
                    elif file_path.endswith(".png"):
                        ctype = "image/png"
                    elif file_path.endswith((".jpg", ".jpeg")):
                        ctype = "image/jpeg"
                    elif file_path.endswith(".gif"):
                        ctype = "image/gif"
                    elif file_path.endswith(".svg"):
                        ctype = "image/svg+xml"
                    self._set_headers(200, content_type=ctype)
                    with open(file_path, "rb") as f:
                        self.wfile.write(f.read())
                    return
            except Exception as e:
                print(f"Error serving static file: {e}")
                self._set_headers(500)
                self.wfile.write(b'{"error":"internal server error"}')
                return
            self._set_headers(404)
            self.wfile.write(b'{"error":"not found"}')
            return

        # API endpoints: /api/analyses
        if path.startswith("/api/analyses"):
            token = self.headers.get("Authorization")
            user = get_user_by_token(token) if token else None
            if not user:
                self._set_headers(401)
                self.wfile.write(b'{"error":"unauthenticated"}'); return

            # Get specific analysis by ID
            if path.startswith("/api/analyses/"):
                analysis_id = path.split("/")[-1]
                try:
                    analysis = analyses_col().find_one({
                        "_id": ObjectId(analysis_id),
                        "user_id": user["_id"]
                    })
                    if not analysis:
                        self._set_headers(404)
                        self.wfile.write(b'{"error":"not found"}')
                        return
                    
                    # Convert ObjectId and datetime objects
                    analysis["_id"] = str(analysis["_id"])
                    analysis["user_id"] = str(analysis["user_id"])
                    analysis["created_at"] = analysis["created_at"].isoformat()
                    
                    self._set_headers(200)
                    self.wfile.write(json.dumps(analysis, default=str).encode())
                    return
                except Exception as e:
                    self._set_headers(500)
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
                    return
            
            # List analyses
            query = parse_qs(parsed.query)
            items = list(analyses_col().find({"user_id": user["_id"]}).sort("created_at",-1).limit(20))
            # convert ObjectId and datetimes
            def clean(x):
                x["_id"] = str(x["_id"])
                x["created_at"] = x["created_at"].isoformat()
                return x
            items = [clean(i) for i in items]
            self._set_headers(200)
            self.wfile.write(json.dumps(items, default=str).encode())
            return

        # API endpoint: GET /api/openrouter/key -> check key status (masked)
        if path == "/api/openrouter/key":
            token = self.headers.get("Authorization")
            user = get_user_by_token(token) if token else None
            if not user:
                self._set_headers(401)
                self.wfile.write(b'{"error":"unauthenticated"}')
                return
            try:
                doc = api_keys_col().find_one({"user_id": user["_id"], "provider": "openrouter"})
                if not doc:
                    self._set_headers(200)
                    self.wfile.write(json.dumps({"exists": False, "provider": "openrouter"}).encode())
                    return
                key = doc.get("key_encrypted", "")
                masked = ("*" * max(0, len(key) - 4)) + key[-4:] if key else ""
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "exists": True,
                    "provider": "openrouter",
                    "masked_key": masked,
                    "updated_at": doc.get("updated_at") and doc["updated_at"].isoformat()
                }).encode())
                return
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return

        # API endpoint: GET /api/recommendations -> latest product recommendations for current user
        if path == "/api/recommendations":
            token = self.headers.get("Authorization")
            user = get_user_by_token(token) if token else None
            if not user:
                self._set_headers(401)
                self.wfile.write(b'{"error":"unauthenticated"}')
                return
            try:
                # Try to get latest analysis with product_recommendations
                last = analyses_col().find({"user_id": user["_id"], "product_recommendations": {"$exists": True, "$ne": []}}).sort("created_at", -1).limit(1)
                last = list(last)
                items = []
                if last:
                    items = last[0].get("product_recommendations", [])
                # If none, fallback to user's history
                if not items:
                    udoc = users_col().find_one({"_id": user["_id"]}, {"product_recommendations": 1}) or {}
                    history = udoc.get("product_recommendations", [])
                    if history:
                        # latest history entry
                        items = (history[-1] or {}).get("items", [])

                # enrich with current product details to ensure fresh data
                ids = [i.get("product_id") for i in items if i.get("product_id")]
                prod_map = {}
                if ids:
                    # Convert IDs to ObjectId where possible
                    obj_ids = []
                    for pid in ids:
                        try:
                            obj_ids.append(ObjectId(str(pid)))
                        except Exception:
                            pass
                    if obj_ids:
                        for p in products_col().find({"_id": {"$in": obj_ids}}):
                            prod_map[str(p["_id"])] = {
                                "name": p.get("name"),
                                "category": p.get("category"),
                                "price": p.get("price"),
                                "tags": p.get("tags", [])
                            }
                result_items = []
                for i in items:
                    pid = str(i.get("product_id"))
                    enriched = {
                        "product_id": pid,
                        "name": i.get("name") or (prod_map.get(pid) or {}).get("name"),
                        "category": i.get("category") or (prod_map.get(pid) or {}).get("category"),
                        "price": i.get("price") or (prod_map.get(pid) or {}).get("price"),
                        "tags": i.get("tags") or (prod_map.get(pid) or {}).get("tags", []),
                        "reason": i.get("reason", "")
                    }
                    result_items.append(enriched)

                self._set_headers(200)
                self.wfile.write(json.dumps({"items": result_items}).encode())
                return
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return

        # API endpoint: GET /api/products -> list products (filters: category, price range, tags; pagination+sorting)
        if path == "/api/products":
            try:
                query = parse_qs(parsed.query)
                q = {}
                if "category" in query:
                    q["category"] = query["category"][0]
                # price range
                price = {}
                if "min_price" in query:
                    try:
                        price["$gte"] = float(query["min_price"][0])
                    except Exception:
                        pass
                if "max_price" in query:
                    try:
                        price["$lte"] = float(query["max_price"][0])
                    except Exception:
                        pass
                if price:
                    q["price"] = price
                # tags (comma separated)
                if "tags" in query:
                    tags_raw = query["tags"][0]
                    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                    if tags:
                        q["tags"] = {"$in": tags}

                # pagination
                limit = max(1, min(100, int(query.get("limit", [12])[0])))
                offset = max(0, int(query.get("offset", [0])[0]))

                # sorting
                sort_key = query.get("sort", [""])[0]
                sort_spec = None
                if sort_key == "price_asc":
                    sort_spec = ("price", 1)
                elif sort_key == "price_desc":
                    sort_spec = ("price", -1)
                elif sort_key == "name_asc":
                    sort_spec = ("name", 1)
                elif sort_key == "name_desc":
                    sort_spec = ("name", -1)
                elif sort_key == "created_desc":
                    sort_spec = ("created_at", -1)

                cur = products_col().find(q)
                if sort_spec:
                    cur = cur.sort([sort_spec])
                total = cur.count() if hasattr(cur, 'count') else products_col().count_documents(q)
                items = list(cur.skip(offset).limit(limit))
                def clean(p):
                    p["_id"] = str(p["_id"])
                    # ensure image_url
                    if not p.get("image_url"):
                        p["image_url"] = "/static/images/placeholder.svg"
                    return p
                items = [clean(p) for p in items]
                self._set_headers(200)
                self.wfile.write(json.dumps({"items": items, "total": total, "limit": limit, "offset": offset}).encode())
                return
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return

        # API endpoint: GET /api/categories -> list distinct categories
        if path == "/api/categories":
            try:
                cats = products_col().distinct("category")
                cats = sorted([c for c in cats if isinstance(c, str)])
                self._set_headers(200)
                self.wfile.write(json.dumps({"items": cats}).encode())
                return
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return

        # API endpoint: GET /api/product/<id> -> single product by id
        if path.startswith("/api/product/"):
            try:
                # slug route: /api/product/slug/<slug>
                if "/slug/" in path:
                    slug = path.split("/slug/")[-1]
                    p = products_col().find_one({"slug": slug})
                else:
                    pid = path.split("/")[-1]
                    p = products_col().find_one({"_id": ObjectId(pid)})
                if not p:
                    self._set_headers(404)
                    self.wfile.write(b'{"error":"not found"}')
                    return
                p["_id"] = str(p["_id"])
                if not p.get("image_url"):
                    p["image_url"] = "/static/images/placeholder.svg"
                self._set_headers(200)
                self.wfile.write(json.dumps(p).encode())
                return
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return

        # API endpoint: GET /api/search?q=... (supports pagination and sorting similar to /api/products)
        if path.startswith("/api/search"):
            try:
                query = parse_qs(parsed.query)
                q = query.get("q", [""])[0].strip()
                filter_q = {}
                if q:
                    filter_q = {"$or": [
                        {"name": {"$regex": q, "$options": "i"}},
                        {"category": {"$regex": q, "$options": "i"}},
                        {"tags": {"$elemMatch": {"$regex": q, "$options": "i"}}},
                    ]}
                # pagination
                limit = max(1, min(100, int(query.get("limit", [12])[0])))
                offset = max(0, int(query.get("offset", [0])[0]))
                # sorting
                sort_key = query.get("sort", [""])[0]
                sort_spec = None
                if sort_key == "price_asc":
                    sort_spec = ("price", 1)
                elif sort_key == "price_desc":
                    sort_spec = ("price", -1)
                elif sort_key == "name_asc":
                    sort_spec = ("name", 1)
                elif sort_key == "name_desc":
                    sort_spec = ("name", -1)
                elif sort_key == "created_desc":
                    sort_spec = ("created_at", -1)

                cur = products_col().find(filter_q)
                if sort_spec:
                    cur = cur.sort([sort_spec])
                total = cur.count() if hasattr(cur, 'count') else products_col().count_documents(filter_q)
                items = list(cur.skip(offset).limit(limit))
                for p in items:
                    p["_id"] = str(p["_id"])
                    if not p.get("image_url"):
                        p["image_url"] = "/static/images/placeholder.svg"
                self._set_headers(200)
                self.wfile.write(json.dumps({"items": items, "total": total, "limit": limit, "offset": offset}).encode())
                return
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
                return

        self._set_headers(404)
        self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        data = read_json(self.rfile, length) if length else {}

        # Signup
        if path == "/api/signup":
            try:
                uid = create_user(data["username"], data["email"], data["password"])
                self._set_headers(201)
                self.wfile.write(json.dumps({"user_id": str(uid)}).encode())
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        # Login
        if path == "/api/login":
            user = users_col().find_one({"username": data.get("username")})
            if not user or not verify_password(data.get("password",""), user["password_hash"]):
                self._set_headers(401)
                self.wfile.write(b'{"error":"invalid"}'); return
            token = create_session(user["_id"])
            self._set_headers(200)
            self.wfile.write(json.dumps({"token": token}).encode())
            return

        # Ingest event
        if path == "/api/ingest":
            try:
                # If caller is authenticated, attach user_id when absent
                token = self.headers.get("Authorization")
                user = get_user_by_token(token) if token else None
                if user and not data.get("user_id"):
                    data["user_id"] = user["_id"]
                eid = ingest_event(data)
                self._set_headers(201)
                self.wfile.write(json.dumps({"event_id": str(eid)}).encode())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        # Request analysis
        if path == "/api/analyze":
            token = self.headers.get("Authorization")
            user = get_user_by_token(token) if token else None
            if not user:
                self._set_headers(401)
                self.wfile.write(b'{"error":"unauthenticated"}'); return
            params = data.get("params", {})
            print(f"API Analysis - User ID: {user['_id']}, Params: {params}")
            try:
                rec = run_analysis(str(user["_id"]), params)
                print(f"API Analysis - Result: {rec.get('spark_summary', {}).get('total_events', 0)} events")
                self._set_headers(200)
                # return id and status
                self.wfile.write(json.dumps({"status":"ok","analysis": {"_id": str(rec.get("_id", ""))}}).encode())
            except Exception as e:
                print(f"API Analysis - Error: {e}")
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        # Set or update OpenRouter API key for current user
        if path == "/api/openrouter/key":
            token = self.headers.get("Authorization")
            user = get_user_by_token(token) if token else None
            if not user:
                self._set_headers(401)
                self.wfile.write(b'{"error":"unauthenticated"}')
                return
            api_key = data.get("api_key")
            if not api_key:
                self._set_headers(400)
                self.wfile.write(b'{"error":"api_key required"}')
                return
            try:
                # Upsert key for provider openrouter
                now = datetime.utcnow()
                api_keys_col().update_one(
                    {"user_id": user["_id"], "provider": "openrouter"},
                    {"$set": {"key_encrypted": api_key, "updated_at": now}, "$setOnInsert": {"created_at": now}},
                    upsert=True
                )
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "ok"}).encode())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        self._set_headers(404)
        self.wfile.write(b'{"error":"not found"}')

if __name__ == "__main__":
    server_address = ("localhost", PORT)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Server running on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()
    except Exception as e:
        print(f"\nError occurred: {e}")
        httpd.server_close()
