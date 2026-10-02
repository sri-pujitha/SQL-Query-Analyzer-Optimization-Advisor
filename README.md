# SQL Query Optimizer

A FastAPI-based tool that analyzes MySQL queries using `EXPLAIN FORMAT=JSON`, visualizes the execution plan as a readable tree, and identifies common query performance issues with actionable suggestions.

## Features

* Analyzes MySQL queries using `EXPLAIN FORMAT=JSON`
* Converts execution plans into a readable tree structure
* Detects common performance issues:

  * Full table scans
  * Filesorts
  * Temporary tables
  * Unused indexes
  * Low filter selectivity
* Provides severity levels and optimization suggestions
* Generates `CREATE INDEX` suggestions where applicable
* Restricts analysis to `SELECT` queries
* Provides a simple web interface for query analysis

## Architecture

```text
┌─────────────┐       POST /api/analyze       ┌──────────────────┐
│  Frontend   │ ────────────────────────────▶ │  FastAPI Backend │
│ HTML/CSS/JS │ ◀──────────────────────────── │                  │
└─────────────┘       Plan + Findings        └────────┬─────────┘
                                                       │
                                                       │ EXPLAIN
                                                       │ FORMAT=JSON
                                                       ▼
                                              ┌──────────────────┐
                                              │   MySQL Server   │
                                              └──────────────────┘
```

## Project Structure

```text
sql-query-optimizer/
│
├── backend/
│   ├── db.py
│   ├── explain_parser.py
│   ├── rules.py
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
└── sample_schema.sql
```

### Backend

* **`backend/db.py`** — manages MySQL connections and executes `EXPLAIN FORMAT=JSON`.
* **`backend/explain_parser.py`** — recursively parses MySQL execution plans and normalizes them into a consistent tree structure.
* **`backend/rules.py`** — applies rule-based checks to identify performance issues and generate optimization suggestions.
* **`backend/main.py`** — FastAPI application exposing the analysis and connection-test endpoints.

### Frontend

The frontend uses vanilla HTML, CSS, and JavaScript. No build system is required.

## Tech Stack

* **Backend:** Python, FastAPI
* **Database:** MySQL
* **Frontend:** HTML, CSS, JavaScript
* **Database Analysis:** MySQL `EXPLAIN FORMAT=JSON`

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/sri-pujitha/sql-query-optimizer.git
cd sql-query-optimizer
```

### 2. Install dependencies

```bash
cd backend
python -m venv venv
```

**Windows:**

```bash
venv\Scripts\activate
```

**Linux/macOS:**

```bash
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 3. Load the sample database

From the project root:

```bash
mysql -u root -p < sample_schema.sql
```

This creates a demo database that can be used to test query analysis and indexing suggestions.

### 4. Start the application

From the `backend` directory:

```bash
uvicorn main:app --reload --port 8000
```

### 5. Open the application

Visit:

`http://localhost:8000`

Enter your MySQL connection details, test the connection, and submit a `SELECT` query for analysis.

## Example

Try:

```sql
SELECT * FROM orders WHERE customer_id = 42;
```

If the column is not indexed, the analyzer can identify the resulting full table scan and provide an indexing suggestion such as:

```sql
CREATE INDEX idx_orders_customer_id
ON orders(customer_id);
```

After adding the index, re-running the analysis can show how the execution plan changes.

## Design Decisions

### Why `EXPLAIN FORMAT=JSON`?

The project uses MySQL's JSON execution plan because it provides structured information that can be parsed programmatically and converted into a readable representation.

`EXPLAIN ANALYZE` was not used because it executes the query and is therefore treated as a potential future enhancement rather than the default analysis method.

### Why SELECT-only?

The application is designed for query analysis rather than arbitrary SQL execution. Restricting input to `SELECT` statements reduces the risk of accidentally modifying data.

### Why rule-based analysis?

The analyzer is intentionally based on explicit rules and heuristics. It focuses on highlighting common execution-plan issues rather than attempting to reproduce MySQL's complete query optimizer.

## Future Improvements

* Support `EXPLAIN ANALYZE` for actual execution statistics
* Add PostgreSQL support
* Compare execution plans before and after index changes
* Track query analysis history
* Add more optimization rules
* Add automated tests for execution-plan parsing and analysis rules

## What I Learned

* Working with FastAPI APIs and backend structure
* Connecting Python applications to MySQL
* Parsing nested JSON execution plans
* Understanding MySQL query execution plans
* Applying rule-based analysis to database performance problems
* Designing a frontend-to-backend workflow for a practical developer tool
