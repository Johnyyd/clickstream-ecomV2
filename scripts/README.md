# Scripts Directory

Organized utility scripts for the clickstream-ecomV2 project.

## Directory Structure

- **`admin/`** - Administrative tools (API key management, user setup)
- **`dev/`** - Development utilities (data seeding, checks, simulation)
- **`maintenance/`** - Database and system maintenance scripts

## Admin Scripts (`admin/`)

| Script                    | Purpose                                |
| ------------------------- | -------------------------------------- |
| `api_key_auto_renewal.py` | Automatic API key rotation and renewal |
| `api_key_manager.py`      | API key CRUD operations                |
| `api_key_utils.py`        | API key utilities and helpers          |
| `setup_admin.py`          | Create admin user account              |

## Dev Scripts (`dev/`)

| Script                    | Purpose                                |
| ------------------------- | -------------------------------------- |
| `check_als_data.py`       | Validate ALS recommendation model data |
| `check_env.py`            | Verify environment configuration       |
| `check_metrics.py`        | Check analytics metrics                |
| `check_paths.py`          | Validate file paths and directories    |
| `check_recent_events.py`  | Inspect recent clickstream events      |
| `seed_products.py`        | Populate product catalog               |
| `seed_realistic_data.py`  | Generate realistic test data           |
| `simulate_clickstream.py` | Simulate user clickstream events       |
| `debug_analysis.py`       | Debug analytics pipeline               |

## Maintenance Scripts (`maintenance/`)

| Script                      | Purpose                          |
| --------------------------- | -------------------------------- |
| `backfill_sessions.py`      | Backfill missing session data    |
| `cleanup_spark_tmp.py`      | Clean Spark temporary files      |
| `export_to_hdfs.py`         | Export data to HDFS              |
| `fix_duplicate_sessions.py` | Remove duplicate session records |
| `fix_empty_sessions.py`     | Fix sessions with missing data   |
| `list_active_users.py`      | List currently active users      |
| `verify_sessions.py`        | Validate session data integrity  |
| `verify_spark_setup.py`     | Verify Spark configuration       |
| `view_analysis_data.py`     | Inspect analysis results         |

## Usage

Run scripts from the project root:

```bash
# Admin
python scripts/admin/setup_admin.py

# Dev
python scripts/dev/seed_products.py
python scripts/dev/simulate_clickstream.py

# Maintenance
python scripts/maintenance/verify_spark_setup.py
python scripts/maintenance/cleanup_spark_tmp.py
```
