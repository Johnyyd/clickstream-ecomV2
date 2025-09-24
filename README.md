# clickstream-ecomV2

Production-like clickstream analytics demo with LLM insights and grounded product recommendations.

## Key Features
- User auth, event ingestion, and lightweight analysis (`server.py`, `ingest.py`, `simple_analysis.py`, `analysis.py`).
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

## Run the Server and Dashboard
```
python server.py
# Open http://localhost:8000
```
- Login or sign up
- Paste your OpenRouter API key and Save
- Optional: choose a model compatible with your key
  ```
  $env:OPENROUTER_MODEL = "openai/gpt-4o-mini"
  ```
- Click "Run Analysis"
- View: Summary, Detailed Metrics, LLM Insights, and Recommended Products

## LLM and Product Recommendations
- `analysis.py/run_analysis()` builds a summarized user context and a subset of the product catalog.
- OpenRouter returns strict JSON with `recommendations_for_user_products`, validated against `products`.
- Recommendations are saved in the analysis document and appended to the user profile for cross-session availability.
- `GET /api/recommendations` returns the latest recommendations, enriched with current product details.

## Project Structure (Selected)
- `server.py` – HTTP server and REST API endpoints.
- `ingest.py` – Ingest events into MongoDB using consistent schema.
- `simple_analysis.py` – Lightweight metrics.
- `analysis.py` – Detailed metrics, LLM orchestration, product-grounded recommendations.
- `openrouter_client.py` – OpenRouter client with strict JSON schema.
- `cleanup_demo_data.py` – Tag/delete noisy/demo events.
- `seed_realistic_data.py` – Canonical realistic seeding (preferred).
- `seed_demo_data.py` – Deprecated, delegates to `seed_realistic_data.py`.
- `seed_products.py` – Seed/expand product catalog.
- `simulate_clickstream.py` – Optional simulator.
- `static/` – Frontend (`index.html`, `dashboard.js`, `styles.css`).

## Notes
- The app intentionally avoids heavy frameworks to keep the codebase approachable.
- For larger datasets, you may want indexes on `events` (e.g., `timestamp`, `user_id`, `session_id`, `flag.noisy`, `properties.source`).
