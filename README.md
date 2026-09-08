# SQL Query Optimizer

A tool that runs EXPLAIN FORMAT=JSON on a MySQL query, displays the 
execution plan as a readable tree, and identifies common performance 
issues such as full table scans, filesorts, temporary tables, 
and unused indexes. It also provides suggestions to help improve
query performance.

## Why this project

I wanted to build a project that helps understand how a database executes a SQL query and how query performance can be improved. MySQL provides execution plans through EXPLAIN FORMAT=JSON, but the output can be difficult to read. This project parses that output and identifies common performance issues.

It combines:

- Parsing the JSON execution plan and converting it into a readable tree
- Rule-based checks for common query performance issues
- A FastAPI backend and simple frontend for analyzing queries and displaying the results

## Architecture

```
┌─────────────┐      POST /api/analyze       ┌──────────────────┐
│  Frontend   │ ───────────────────────────▶ │  FastAPI backend │
│ (HTML/JS)   │ ◀─────────────────────────── │                  │
└─────────────┘      plan tree + findings    └────────┬─────────┘
                                                        │ EXPLAIN FORMAT=JSON
                                                        ▼
                                              ┌──────────────────┐
                                              │   MySQL server    │
                                              └──────────────────┘
```

- **backend/db.py** — Connects to MySQL and runs EXPLAIN FORMAT=JSON for the query.
- **backend/explain_parser.py** — Parses the JSON execution plan and converts it into a readable tree structure.
- **backend/rules.py** — Checks the execution plan for common issues such as full table scans, filesorts, temporary tables, unused indexes, and low filter selectivity. It also provides suggestions for improving the query.
- **backend/main.py** — Contains the FastAPI application and provides the /api/connect-test and /api/analyze endpoints. It also serves the frontend.
- **frontend/** — Contains the HTML, CSS, and JavaScript files used for the user interface.

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

Against the sample schema, this should be flagged as a full table scan with a suggested CREATE INDEX statement. Run the suggested statement and analyze the same query again to see if the issue is resolved.

## Design decisions & trade-offs

- **`EXPLAIN FORMAT=JSON` over `EXPLAIN ANALYZE`** — The project uses EXPLAIN FORMAT=JSON to get the query execution plan without actually executing the query. EXPLAIN ANALYZE could be added in a future version to compare estimated and actual execution details.
- **SELECT-only restriction** — The API only accepts SELECT queries because the purpose of the project is to analyze queries rather than execute other types of SQL statements.
- **Heuristic rules, not a query planner** — The project uses rule-based checks to identify common performance issues. It does not try to replace MySQL's query optimizer or cost model.

## Possible extensions

- Support EXPLAIN ANALYZE FORMAT=JSON to compare estimated and actual row counts
- Add PostgreSQL support alongside MySQL
- Track query history and compare execution plans before and after an index change
- Apply suggested indexes to a test database and re-run EXPLAIN to measure the improvement
