# ID Standardization and Data Consistency Summary

## Overview
Comprehensive standardization of ID fields across the codebase to use ObjectId consistently, remove unnecessary fields, and ensure foreign key consistency between collections.

## Changes Made

### 1. Core Ingestion (`ingest.py`)
- **ObjectId Coercion**: All incoming `user_id` values are now coerced to `ObjectId` when possible, `None` if invalid
- **Simplified Logic**: Removed redundant session_id generation logic
- **Field Cleanup**: Removed unnecessary `created_at` field from sessions collection
- **Consistency**: Ensures all new data uses ObjectId for user references

### 2. Data Generation Files

#### `seed_products.py`
- **Import Optimization**: Direct collection import instead of `get_db()`
- **Field Cleanup**: Removed unnecessary `created_at` timestamp
- **Simplified Logic**: Streamlined product creation process
- **ObjectId Usage**: Proper ObjectId generation for product IDs

#### `seed_realistic_data.py`
- **User ID Consistency**: Pass `user_id` as string to `ingest_event()` (which then converts to ObjectId)
- **ObjectId Handling**: Proper ObjectId creation for new users
- **Field Cleanup**: Removed unnecessary `created_at` from session documents
- **Simplified Logic**: Removed redundant user role setting and error handling

#### `seed_demo_data.py`
- **User ID Consistency**: Convert `user_id` to string before passing to `ingest_event()`
- **ObjectId Handling**: Proper ObjectId conversion for user creation
- **Performance**: Removed unnecessary product count check
- **Consistency**: Aligned with realistic data seeding patterns

#### `simulate_clickstream.py`
- **User ID Consistency**: Convert ObjectId to string before creating session data
- **Simplified Logic**: Cleaner user ID handling in session creation

#### `backfill_sessions.py`
- **Field Cleanup**: Removed unnecessary `created_at` field from session backfill

### 3. Migration Script
- **Created**: `scripts/migrate_ids_to_objectid.py`
- **Purpose**: Convert existing string `user_id` fields to ObjectId in events, sessions, and analyses collections
- **Batch Processing**: Handles large datasets efficiently with 1000-document batches
- **Safety**: Only converts valid 24-character hex strings to ObjectId

### 4. Frontend Simulation Fix (`static/dashboard.js`)
- **User Context**: Fetch current user ID after login
- **Simulation Enhancement**: Include logged-in user's ID in simulated events
- **Session Consistency**: Use consistent session ID for simulation batches

## Data Model Consistency

### Primary Keys
- **events**: `_id` (MongoDB ObjectId)
- **sessions**: `_id` (MongoDB ObjectId)
- **users**: `_id` (MongoDB ObjectId)
- **products**: `_id` (MongoDB ObjectId)
- **analyses**: `_id` (MongoDB ObjectId)

### Foreign Key Relationships
- **events.user_id** → **users._id** (ObjectId)
- **events.session_id** → **sessions.session_id** (String)
- **sessions.user_id** → **users._id** (ObjectId)
- **analyses.user_id** → **users._id** (ObjectId)

### Field Standardization
**Removed unnecessary fields:**
- `created_at` from products (not needed for catalog items)
- `created_at` from sessions (use `first_event_at` instead)
- Redundant role setting in user creation

**Standardized fields:**
- All `user_id` references use ObjectId consistently
- Session IDs remain strings for readability
- Event timestamps use UTC datetime objects

## Benefits

1. **Query Consistency**: All user-based queries now work with ObjectId without type conversion
2. **Data Integrity**: Foreign key relationships are properly typed
3. **Storage Efficiency**: Removed redundant fields reduces document size
4. **Analysis Accuracy**: Per-user analysis now correctly filters by ObjectId
5. **Simulation Realism**: Simulated events are properly associated with logged-in users

## Migration Steps

1. **Run Migration**: `python scripts/migrate_ids_to_objectid.py`
2. **Verify Data**: Check that user_id fields are ObjectId type in MongoDB
3. **Test Analysis**: Run per-user analysis to confirm filtering works
4. **Test Simulation**: Use "Simulate Events (10)" button to verify user association

## Files Modified

- `ingest.py` - Core ingestion logic
- `seed_products.py` - Product seeding
- `seed_realistic_data.py` - Realistic data generation
- `seed_demo_data.py` - Demo data generation
- `simulate_clickstream.py` - Clickstream simulation
- `backfill_sessions.py` - Session backfill utility
- `static/dashboard.js` - Frontend simulation
- `scripts/migrate_ids_to_objectid.py` - Migration script (new)

## Validation

After migration, verify:
- `db.events.findOne({user_id: {$type: 'objectId'}})` returns documents
- `db.sessions.findOne({user_id: {$type: 'objectId'}})` returns documents
- Per-user analysis includes simulated events
- Event counts are consistent between collections
