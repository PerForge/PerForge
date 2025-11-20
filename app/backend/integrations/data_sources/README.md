# Data Sources Integration Guide

This folder contains backend integrations for external data sources used by PerForge (e.g. InfluxDB).

It also provides **base abstraction layers** that every data source must implement:

- `base_extraction.py` – common read/extraction interface
- `base_insertion.py` – common write/insertion interface
- `base_queries.py` – abstract query builders for backend and frontend metrics

Use this document as a **step‑by‑step guide** when adding a new data source implementation (for example, `influxdb_v1.8`).

---

## 1. Understand the Architecture

Each data source typically has its own subfolder, for example:

- `influxdb_v2/`
- `influxdb_v1.8/`

Inside a data source folder you will usually find:

- `influxdb_db.py` – low‑level DB/client wrapper (connection, auth, helpers)
- `influxdb_extraction.py` – concrete implementation of `DataExtractionBase`
- `influxdb_insertion.py` – concrete implementation of `DataInsertionBase`
- `queries/` – concrete implementations of `BackEndQueriesBase` and/or `FrontEndQueriesBase` from `base_queries.py`

These pieces work together as follows:

1. **Queries**: Build data‑source‑specific query strings (SQL/Flux/HTTP params).
2. **DB client**: Executes those queries against the external system.
3. **Extraction/Insertion classes**: Provide a uniform Python API to the rest of PerForge, converting raw responses into normalized structures (dicts, DataFrames, etc.) according to the contracts in `base_extraction.py` / `base_insertion.py`.

---

## 2. Create the New Data Source Folder

1. Under `app/backend/integrations/data_sources`, create a new folder, e.g.:
   - `my_data_source/`
2. Within that folder create the basic structure:
   - `my_data_source_db.py`
   - `my_data_source_extraction.py`
   - `my_data_source_insertion.py` (optional if you only support reads)
   - `queries/` subfolder for query builders

You can use the existing `influxdb_v2/` and `influxdb_v1.8/` folders as **reference templates**.

---

## 3. Implement Query Builders (`queries/`)

1. In `queries/`, create modules for backend/frontend queries, for example:
   - `backend_queries.py`
   - `frontend_queries.py`

2. Implement classes that inherit from `BackEndQueriesBase` and/or `FrontEndQueriesBase` (see `base_queries.py`).

3. For each abstract method in the base classes, implement a concrete method that:
   - Accepts the same parameters as defined in the base
   - Returns a **query string** (or structure) that your DB client understands

Examples of responsibilities:

- Backend queries: test log, throughput, response time metrics, error counts, per‑transaction stats
- Frontend queries: Google Web Vitals, timings, CPU long tasks, JS heap metrics, content types, transfer sizes, overview data

**Important:** Keep these classes **query‑building only**; the actual execution should be done via the DB client.

---

## 4. Implement the DB Client (`*_db.py`)

1. Create a class (e.g. `MyDataSourceDB`) that encapsulates:
   - Connection configuration (URL, token, org, bucket, etc.)
   - Client initialization and closing
   - A method to execute arbitrary queries and return raw results

2. Typical responsibilities:
   - Map PerForge integration configuration (stored in the project) to the data source connection settings
   - Handle retries / basic error handling
   - Provide helper methods like `query_backend(query: str)` and `query_frontend(query: str)` when appropriate

`influxdb_v2/influxdb_db.py` is a good concrete example of how this is done.

---

## 5. Implement Data Extraction (`*_extraction.py`)

1. Create a class that **inherits from** `DataExtractionBase` (from `base_extraction.py`), for example:
   - `MyDataSourceExtraction(DataExtractionBase)`

2. Implement the required abstract methods:

   - Configuration & lifecycle:
     - `set_config(...)`
     - `_initialize_client()`
     - `_close_client()`

   - Backend test metadata:
     - `_fetch_test_log(...)`
     - `_fetch_tests_titles()`
     - `_fetch_start_time(...)`
     - `_fetch_end_time(...)`

   - Backend metrics:
     - `_fetch_aggregated_data(...)`
     - `_fetch_rps(...)`
     - `_fetch_active_threads(...)`
     - `_fetch_average_response_time(...)`
     - `_fetch_median_response_time(...)`
     - `_fetch_pct90_response_time(...)`
     - `_fetch_error_count(...)`
     - `_fetch_average_response_time_per_req(...)`
     - `_fetch_median_response_time_per_req(...)`
     - `_fetch_pct90_response_time_per_req(...)`
     - `_fetch_throughput_per_req(...)`
     - `_fetch_max_active_users_stats(...)`
     - `_fetch_median_throughput_stats(...)`
     - `_fetch_median_response_time_stats(...)`
     - `_fetch_pct90_response_time_stats(...)`
     - `_fetch_errors_pct_stats(...)`

   - Frontend metrics:
     - `_fetch_overview_data(...)`
     - `_fetch_google_web_vitals(...)`
     - `_fetch_timings_fully_loaded(...)`
     - `_fetch_timings_page_timings(...)`
     - `_fetch_timings_main_document(...)`
     - `_fetch_cpu_long_tasks(...)`
     - `_fetch_cdp_performance_js_heap_used_size(...)`
     - `_fetch_cdp_performance_js_heap_total_size(...)`
     - `_fetch_count_per_content_type(...)`
     - `_fetch_first_party_transfer_size(...)`
     - `_fetch_third_party_transfer_size(...)`

3. Inside each `_fetch_*` method:

   - Use your **query builder** class to generate the query string
   - Use your **DB client** to execute the query
   - Convert the raw response to the **expected output type**:
     - Lists of dicts with specific keys
     - `pandas.DataFrame` with required index/columns
     - `int` / `float` for scalar metrics

The decorators and helper methods in `DataExtractionBase` (e.g. `validate_*` functions) will validate the shape of your outputs.

---

## 6. Implement Data Insertion (`*_insertion.py`, Optional)

If your data source also supports **writing** metrics:

1. Create a class that inherits from `DataInsertionBase` (see `base_insertion.py`), for example:
   - `MyDataSourceInsertion(DataInsertionBase)`

2. Implement:
   - `set_config(id: int | None)` – load integration config and prepare connection details
   - `_initialize_client()` / `_close_client()` – manage the underlying client
   - `write_upload(df, test_title, write_events=True, aggregation_window="5s")` – write normalized metrics into the store

3. Ensure `write_upload` returns a dict like:

   - `{ "points_written": <int> }`

Use `influxdb_v2/influxdb_insertion.py` (and the new `influxdb_v1.8` insertion implementation) as guidance.

---

## 7. Wire the New Data Source into the Application

After implementing queries, DB client, and extraction/insertion:

1. **Register the integration type** in the PerForge configuration/models so that it appears as a selectable data source in the UI.
2. Make sure the integration settings (host, port, credentials, bucket, etc.) are stored and passed to your new classes.
3. Update any **factory** or **dispatch** logic that chooses the correct `DataExtractionBase` / `DataInsertionBase` subclass based on the configured data source type.
4. Verify that reporting and analysis modules can consume the metrics from your new implementation without any code changes (they should, as long as you follow the base contracts).

---

## 8. Testing Checklist

When adding a new data source, verify at least the following:

- **Connection**
  - Can initialize and close the client without errors.

- **Smoke tests**
  - `get_tests_titles()` returns a non‑empty list for a known dataset.
  - `get_test_log(...)` returns valid entries with required keys.

- **Backend metrics**
  - Overall metrics (throughput, users, response times, errors) match what the source system shows.
  - Per‑transaction metrics are correctly mapped and aggregated.

- **Frontend metrics (if applicable)**
  - Google Web Vitals and timing metrics are returned with correct units and names.
  - Content types and transfer sizes are correctly separated into first‑party and third‑party.

- **Insertion (if implemented)**
  - Upload a small dataset with `write_upload` and confirm it appears in the source system.

---

## 9. Using InfluxDB Integrations as Reference

The best way to implement a new data source is to **mirror the approach used by InfluxDB integrations**:

- `influxdb_v2/` – modern reference implementation (queries, extraction, insertion).
- `influxdb_v1.8/` – variant specifically tailored to InfluxDB 1.8.

When in doubt, copy the structure from these folders and adapt:

- Class names and imports
- Query syntax
- Response parsing
- Configuration fields

This ensures your new data source behaves consistently with the rest of the PerForge architecture and is easy to maintain.
