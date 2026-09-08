"""
db.py
Handles short-lived MySQL connections used purely to run EXPLAIN on a
user-supplied query. Credentials are never stored - they're passed in
per-request from the frontend and the connection is closed immediately
after use.
"""

import pymysql
import pymysql.cursors
from typing import Any, Dict


class DBConnectionError(Exception):
    """Raised when we can't connect to the target MySQL server."""
    pass


class QueryExecutionError(Exception):
    """Raised when EXPLAIN itself fails (bad SQL, missing table, etc.)."""
    pass


def get_connection(host: str, port: int, user: str, password: str, database: str):
    try:
        return pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
    except pymysql.MySQLError as e:
        raise DBConnectionError(str(e))


def test_connection(host: str, port: int, user: str, password: str, database: str) -> Dict[str, Any]:
    conn = get_connection(host, port, user, password, database)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS version")
            row = cur.fetchone()
        return {"success": True, "mysql_version": row["version"]}
    finally:
        conn.close()


def run_explain_json(host: str, port: int, user: str, password: str, database: str, query: str) -> str:
    """
    Runs EXPLAIN FORMAT=JSON on the given query and returns the raw JSON string
    MySQL produces. Caller is responsible for validating the query is a SELECT.
    """
    conn = get_connection(host, port, user, password, database)
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(f"EXPLAIN FORMAT=JSON {query}")
            except pymysql.MySQLError as e:
                raise QueryExecutionError(str(e))
            row = cur.fetchone()
            if not row:
                raise QueryExecutionError("EXPLAIN returned no output.")
            # The JSON plan is returned under the key "EXPLAIN"
            return row.get("EXPLAIN") or list(row.values())[0]
    finally:
        conn.close()
