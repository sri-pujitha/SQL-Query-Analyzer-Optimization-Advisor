"""
main.py
FastAPI backend for the SQL Query Optimizer/Analyzer tool.

Run locally with:
    uvicorn main:app --reload --port 8000

Then open frontend/index.html in your browser (or see README for serving
it directly from this app).
"""

import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db import test_connection, run_explain_json, DBConnectionError, QueryExecutionError
from explain_parser import parse_explain_json
from rules import analyze

app = FastAPI(title="SQL Query Optimizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev tool only - fine to leave open
    allow_methods=["*"],
    allow_headers=["*"],
)

SELECT_ONLY = re.compile(r"^\s*(--.*\n|\s)*select\b", re.IGNORECASE)


class ConnectionInfo(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str
    password: str = ""
    database: str


class AnalyzeRequest(ConnectionInfo):
    query: str


@app.post("/api/connect-test")
def connect_test(payload: ConnectionInfo):
    try:
        result = test_connection(
            payload.host, payload.port, payload.user, payload.password, payload.database
        )
        return result
    except DBConnectionError as e:
        raise HTTPException(status_code=400, detail=f"Could not connect: {e}")


@app.post("/api/analyze")
def analyze_query(payload: AnalyzeRequest):
    if not SELECT_ONLY.match(payload.query or ""):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are supported (safety restriction).",
        )

    try:
        raw_json = run_explain_json(
            payload.host, payload.port, payload.user, payload.password,
            payload.database, payload.query,
        )
    except DBConnectionError as e:
        raise HTTPException(status_code=400, detail=f"Could not connect: {e}")
    except QueryExecutionError as e:
        raise HTTPException(status_code=400, detail=f"EXPLAIN failed: {e}")

    try:
        tree = parse_explain_json(raw_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse EXPLAIN output: {e}")

    findings = analyze(tree)

    return {
        "tree": tree,
        "findings": findings,
        "raw_explain_json": raw_json,
    }


# --- Serve the frontend directly from FastAPI for convenience ---
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
