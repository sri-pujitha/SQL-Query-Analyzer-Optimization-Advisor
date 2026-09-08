"""
rules.py
A small rule engine that walks the normalized EXPLAIN tree and produces
plain-English findings with a severity level. This is intentionally
heuristic (not a query planner) - it's meant to surface the same red flags
an experienced DBA would look for by eye.
"""

import re
from typing import Any, Dict, List

FULL_SCAN_TYPES = {"ALL"}
WEAK_SCAN_TYPES = {"index"}  # scans the whole index, better than ALL but still not a seek

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def analyze(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    _walk(tree, findings)
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 9))
    return findings


def _walk(node: Dict[str, Any], findings: List[Dict[str, Any]]) -> None:
    node_type = node.get("node_type")

    if node_type == "TABLE":
        findings.extend(_check_table(node))
    elif node_type in ("ORDER_BY", "GROUP_BY", "DISTINCT"):
        findings.extend(_check_wrapper(node))

    for child in node.get("children", []):
        _walk(child, findings)


def _check_table(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    table = node.get("table_name") or "a derived table"
    access_type = node.get("access_type")
    rows = node.get("rows_examined")
    key = node.get("key")
    possible_keys = node.get("possible_keys") or []
    filtered = node.get("filtered_percent")
    condition = node.get("attached_condition")

    if access_type in FULL_SCAN_TYPES:
        severity = "high" if (rows or 0) > 1000 else "medium"
        suggestion = _suggest_index(table, condition, possible_keys)
        out.append({
            "severity": severity,
            "title": f"Full table scan on `{table}`",
            "detail": (
                f"MySQL is reading every row of `{table}` (access type ALL)"
                + (f", examining ~{rows} rows per scan." if rows else ".")
            ),
            "suggestion": suggestion,
        })
    elif access_type in WEAK_SCAN_TYPES:
        out.append({
            "severity": "medium",
            "title": f"Full index scan on `{table}`",
            "detail": (
                f"MySQL is scanning the entire index on `{table}` rather than "
                "seeking to specific rows. Better than a table scan, but still "
                "reads more data than necessary."
            ),
            "suggestion": "Check whether a more selective composite index matches your WHERE clause.",
        })

    if access_type not in FULL_SCAN_TYPES and not key and possible_keys:
        out.append({
            "severity": "medium",
            "title": f"Usable index not chosen on `{table}`",
            "detail": (
                f"MySQL considered indexes ({', '.join(possible_keys)}) on `{table}` "
                "but decided not to use any of them, often because the optimizer "
                "estimated a full scan would be cheaper."
            ),
            "suggestion": "Verify table statistics are current (ANALYZE TABLE) or check if the query can be rewritten to be more selective.",
        })

    if filtered is not None and filtered < 20 and (rows or 0) > 1000:
        out.append({
            "severity": "low",
            "title": f"Low filter selectivity on `{table}`",
            "detail": (
                f"Only about {filtered:.1f}% of the ~{rows} examined rows on `{table}` "
                "actually match the query's conditions - most of the scanned work is discarded."
            ),
            "suggestion": "Consider an index that covers the filtering columns so fewer rows need to be examined in the first place.",
        })

    return out


def _check_wrapper(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    label = node.get("label", "operation")

    if node.get("using_filesort"):
        out.append({
            "severity": "medium",
            "title": f"Filesort required for {label}",
            "detail": (
                "MySQL couldn't use an index to satisfy the sort order and had to "
                "sort the result set separately (in memory or on disk)."
            ),
            "suggestion": "Add an index whose column order matches your ORDER BY clause so MySQL can read rows already sorted.",
        })

    if node.get("using_temporary_table"):
        out.append({
            "severity": "medium",
            "title": f"Temporary table required for {label}",
            "detail": (
                "MySQL had to materialize an intermediate temporary table to "
                "complete this operation, which adds I/O and memory overhead."
            ),
            "suggestion": "Often fixable with a covering index on the GROUP BY / DISTINCT columns, or by reducing the columns selected.",
        })

    return out


_COLUMN_PATTERN = re.compile(r"`([a-zA-Z0-9_]+)`\.`([a-zA-Z0-9_]+)`\s*(?:=|<|>|<=|>=)")


def _suggest_index(table: str, condition: str, possible_keys: List[str]) -> str:
    if possible_keys:
        return (
            f"MySQL has candidate indexes ({', '.join(possible_keys)}) but chose not "
            "to use them - double check selectivity and table statistics before adding new ones."
        )

    if condition:
        cols = sorted(set(
            col for tbl, col in _COLUMN_PATTERN.findall(condition) if tbl == table
        ))
        if cols:
            col_list = ", ".join(cols)
            return f"Consider adding an index: `CREATE INDEX idx_{table}_{'_'.join(cols)} ON {table} ({col_list});`"

    return f"No index currently covers this access pattern on `{table}` - review the WHERE/JOIN columns used against it."
