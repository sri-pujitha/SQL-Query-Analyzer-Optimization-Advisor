# SQL Query Optimizer

A tool that runs `EXPLAIN FORMAT=JSON` on a MySQL query, renders the
execution plan as a readable tree, and flags common performance problems
(full table scans, filesorts, temporary tables, unused indexes) with
concrete suggestions - the kind of review an experienced DBA does by eye.

## Why this project

Most portfolio projects are CRUD apps. This one demonstrates something
rarer and more senior: understanding *how a database actually executes a
query*, not just how to write one. It combines:
- Parsing and normalizing a semi-structured, version-dependent JSON format
- A rule-based analysis engine (the same category of logic behind real
  tools like `pt-query-digest` or Postgres's `pganalyze`)
- A clean API + UI that turns a wall of JSON into something a developer
  can act on in seconds

## Architecture

```
┌─────────────┐      POST /api/analyze      ┌──────────────────┐
│  Frontend   │ ───────────────────────────▶ │  FastAPI backend │
│ (HTML/JS)   │ ◀─────────────────────────── │                  │
└─────────────┘      plan tree + findings    └────────┬─────────┘
                                                        │ EXPLAIN FORMAT=JSON
                                                        ▼
                                              ┌──────────────────┐
                                              │   MySQL server    │
                                              └──────────────────┘
```

- **`backend/db.py`** — opens a short-lived MySQL connection per request
  (credentials are never stored) and runs `EXPLAIN FORMAT=JSON`.
- **`backend/explain_parser.py`** — MySQL's JSON plan shape varies a lot
  depending on the query (joins, subqueries, unions, sorts). This module
  walks it recursively and normalizes it into one consistent tree shape.
- **`backend/rules.py`** — the analysis engine. Walks the normalized tree
  and applies heuristics: full scans, unused indexes, filesorts, temp
  tables, low filter selectivity — each with a severity and a suggested
  fix, including generated `CREATE INDEX` statements where possible.
- **`backend/main.py`** — FastAPI app exposing `/api/connect-test` and
  `/api/analyze`, and serving the frontend as static files.
- **`frontend/`** — vanilla HTML/CSS/JS. No build step required.

## Setup

### 1. Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. (Optional) Load sample data to test with

```bash
mysql -u root -p < ../sample_schema.sql
```

This creates a `query_optimizer_demo` database with an intentionally
unindexed column so you have something to detect and fix on your first run.

### 3. Run the backend

```bash
uvicorn main:app --reload --port 8000
```

### 4. Open the app

Visit **http://localhost:8000** — the frontend is served directly by
FastAPI, so no separate server is needed.

Fill in your MySQL connection details (or the demo database from step 2),
click **Test Connection**, paste a `SELECT` query, and click **Analyze
Query**.

## Try it

```sql
SELECT * FROM orders WHERE customer_id = 42;
```

Against the sample schema, this should be flagged as a **full table scan**
with a suggested `CREATE INDEX` statement. Run that statement, re-analyze
the same query, and watch the finding disappear — a nice before/after to
show in an interview or demo video.

## Design decisions & trade-offs

- **`EXPLAIN FORMAT=JSON` over `EXPLAIN ANALYZE`** — plain `EXPLAIN` uses
  the optimizer's *estimates*, not actual execution stats, which means it's
  safe to run even on write-heavy production tables without side effects.
  `EXPLAIN ANALYZE` (which actually runs the query) was left as a natural
  "v2" extension.
- **SELECT-only restriction** — the API rejects anything that isn't a
  `SELECT`, since this tool is for *analyzing* queries, not running
  arbitrary SQL against a user's database.
- **Heuristic rules, not a query planner** — the goal is surfacing the same
  red flags a human reviewer would notice, not perfectly replicating
  MySQL's cost model.

## Possible extensions (good "what I'd do next" talking points)

- Support `EXPLAIN ANALYZE FORMAT=JSON` for actual vs. estimated row counts
- Add PostgreSQL support alongside MySQL
- Track query history and diff plans before/after an index change
- Auto-apply suggested indexes to a scratch/staging copy and re-run EXPLAIN
  to quantify the improvement
