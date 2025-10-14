# clickstream-ecomV2

Production-like clickstream analytics demo with LLM insights and grounded product recommendations.

## Key Features
- User auth, event ingestion, and analysis (FastAPI: `app/main.py`, modular routers in `app/api/`, `ingest.py`, `simple_analysis.py`, `analysis.py`).
- LLM insights via OpenRouter (`openrouter_client.py`) with strict JSON and product-grounded recommendations.
- Frontend dashboard to run analysis and view “Recommended Products” (`static/`).

## Consolidation and Cleanup
To reduce duplication and keep a single source of truth for data generation:
- Deprecated wrapper: `seed_demo_data.py` now delegates to `seed_realistic_data.py`.
- Canonical realistic seeding: `seed_realistic_data.py` (preferred).
- Optional simulator: `simulate_clickstream.py` remains for ad-hoc simulations.
- Noisy/demo data cleaning: `cleanup_demo_data.py` (non-destructive by default).

Analysis filters exclude noisy sources by default (while preserving schema):
- Excludes `flag.noisy == true` and sources in `["simulation", "basic_sim", "seed_demo"]`.
- Source `"realistic_seed"` is included (counted as good data) so you can identify it if needed.

## Setup
```
& venv\Scripts\Activate.ps1
$env:MONGO_URI = "mongodb://localhost:27017"   # optional override
$env:MONGO_DB = "clickstream"               # optional override
```

## Seed Products
If your products collection is empty, seed it first:
```
python seed_products.py
```

## Seed Realistic Customer-like Data (Preferred)
```
# 7 days, 25 users, 5 sessions/user/day, ~7 events/session
python seed_realistic_data.py --days 7 --user-count 25 --sessions-per-user 5 --avg-events 7 --seed-products

# One specific user
python seed_realistic_data.py --username alice --days 5 --sessions-per-user 3 --avg-events 6 --seed-products
```

## Clean Up Noisy/Demo Data
```
# Dry-run statistics
python cleanup_demo_data.py --dry-run

# Tag noisy events (non-destructive)
python cleanup_demo_data.py

# Delete flagged events (optional, destructive)
python cleanup_demo_data.py --delete

# Consider only recent N days
python cleanup_demo_data.py --since-days 14
```

## Run the Server and Dashboard (FastAPI)

Recommended via Docker Compose (FastAPI is default):
```
docker compose build
docker compose up -d

# App:       http://localhost:8000
# Dashboard: http://localhost:8000/dashboard
# Mongo-Express: http://localhost:8081
```

Run locally without Docker (FastAPI):
```
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Quick start (dashboard):
- Login or sign up at `/dashboard` or use `static/auth.html`.
- (Optional) Manage OpenRouter key at `/api/openrouter/*` or use auto-provision if configured.
- Click "Run Analysis".
- View: Summary, Detailed Metrics, LLM Insights, and Recommended Products.

## LLM and Product Recommendations
- `analysis.py/run_analysis()` builds a summarized user context and a subset of the product catalog.
- OpenRouter returns strict JSON with `recommendations_for_user_products`, validated against `products`.
- Recommendations are saved in the analysis document and appended to the user profile for cross-session availability.
- `GET /api/recommendations` returns the latest recommendations, enriched with current product details.

## Project Structure (Selected)
- `app/main.py` – FastAPI application (CORS, static, pretty routes, router includes).
- `app/api/*.py` – Modular routers (`events`, `products`, `auth`, `analyses`, `analysis`, `openrouter`, `recommendations`).
- `ingest.py` – Ingest events into MongoDB using consistent schema (optional Kafka forward).
- `jobs/clickstream_streaming.py` – Spark Structured Streaming job (Kafka → aggregates → MongoDB).
- `app/repositories/indexes.py` – Ensures MongoDB indexes on startup.
- `simple_analysis.py` – Lightweight metrics.
- `analysis.py` – Detailed metrics, LLM orchestration, product-grounded recommendations.
- `openrouter_client.py` – OpenRouter client with strict JSON schema.
- `cleanup_demo_data.py` – Tag/delete noisy/demo events.
- `seed_realistic_data.py` – Canonical realistic seeding (preferred).
- `seed_demo_data.py` – Deprecated, delegates to `seed_realistic_data.py`.
- `seed_products.py` – Seed/expand product catalog.
- `simulate_clickstream.py` – Optional simulator.
- `static/` – Frontend (`index.html`, `dashboard.js`, `styles.css`).
  - `analytics.js` – Lightweight analytics SDK with batching to `/api/ingest-batch`.
  - `auth.html` – Simple auth page (login/signup).

## Data Pipeline (Kafka + Spark Streaming)

Compose includes Zookeeper, Kafka, Spark master/worker. Create Kafka topic once:
```
docker exec -it $(docker ps -qf name=kafka) bash -lc \
  'kafka-topics --create --topic clickstream.events --bootstrap-server kafka:29092 --replication-factor 1 --partitions 3 || true'
```

Submit streaming job (from a Spark container):
```
docker exec -it $(docker ps -qf name=spark-master) bash -lc \
  'spark-submit --master spark://spark-master:7077 /app/jobs/clickstream_streaming.py'
```

Streaming aggregates are written to Mongo collection `aggregates_minute`.

## Event Tracking (Frontend)

- All storefront pages include `static/analytics.js`. It batches events to `/api/ingest-batch`.
- `static/shop.js` still posts per-event to `/api/ingest` for backward compat.

## API Endpoints (FastAPI)

- Events: `POST /api/ingest`, `POST /api/ingest-batch`
- Products: `GET /api/products`, `GET /api/categories`, `GET /api/product/{id}`, `GET /api/product/slug/{slug}`, `GET /api/search`
- Auth: `POST /api/signup`, `POST /api/login`
- Analyses: `GET /api/analyses`, `GET /api/analyses/{id}`
- Analysis run/mode: `POST /api/analyze`, `GET /api/analysis/mode`
- OpenRouter: `GET/POST/DELETE /api/openrouter/key`, `POST /api/openrouter/provision`
- Recommendations: `GET /api/recommendations`

## Environment Variables

- `MONGO_URI` (default `mongodb://mongo:27017`)
- `MONGO_DB` (default `clickstream`)
- `USE_SPARK` (`true`|`false`) – default engine; can be overridden per-request with `params.use_spark`.
- `KAFKA_BROKERS` (optional `host:port`) and `KAFKA_TOPIC` (default `clickstream.events`) for event forwarding.
- `OPENROUTER_PROVISIONING_KEY` (optional; enables runtime key provisioning).

## Notes
- The app intentionally avoids heavy frameworks to keep the codebase approachable.
- For larger datasets, you may want indexes on `events` (e.g., `timestamp`, `user_id`, `session_id`, `flag.noisy`, `properties.source`).
