# server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, urllib
from urllib.parse import urlparse, parse_qs
from ingest import ingest_event
from auth import create_user, create_session, get_user_by_token, verify_password, hash_password
from analysis import run_analysis
from db import users_col, analyses_col
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
        if path == "/" or path.endswith((".html", ".css", ".js")):
            # serve static files
            try:
                if path == "/":
                    file_path = os.path.join(STATIC_DIR, "index.html")
                else:
                    # Remove leading slash and 'static/' if present
                    rel = path.lstrip("/").replace("static/", "")
                    file_path = os.path.join(STATIC_DIR, rel)
                
                # Kiểm tra path traversal
                file_path = os.path.normpath(file_path)
                if not file_path.startswith(STATIC_DIR):
                    self._set_headers(403)
                    self.wfile.write(b'{"error":"forbidden"}')
                    return
                    
                if os.path.exists(file_path):
                    ctype = "text/html" if file_path.endswith(".html") else "text/css" if file_path.endswith(".css") else "application/javascript"
                    self._set_headers(200, content_type=ctype)
                    with open(file_path, "rb") as f:
                        self.wfile.write(f.read())
                    return
            except Exception as e:
                print(f"Error serving static file: {e}")
                self._set_headers(500)
                self.wfile.write(b'{"error":"internal server error"}')
            if os.path.exists(file_path):
                ctype = "text/html" if file_path.endswith(".html") else "text/css" if file_path.endswith(".css") else "application/javascript"
                self._set_headers(200, content_type=ctype)
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
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
