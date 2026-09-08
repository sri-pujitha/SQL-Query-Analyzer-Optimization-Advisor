"""
explain_parser.py
Normalizes MySQL's EXPLAIN FORMAT=JSON output (which varies quite a bit in
shape depending on the query) into a simple, consistent tree of nodes that
the frontend can render and the rules engine can reason about.

Each normalized node looks like:
{
    "node_type": "TABLE" | "NESTED_LOOP" | "ORDER_BY" | "GROUP_BY" |
                 "DISTINCT" | "UNION" | "SUBQUERY",
    "label": human-readable summary,
    "table_name": str | None,
    "access_type": str | None,
    "possible_keys": list[str],
    "key": str | None,
    "rows_examined": int | None,
    "filtered_percent": float | None,
    "using_filesort": bool,
    "using_temporary_table": bool,
    "attached_condition": str | None,
    "children": [ ...normalized nodes... ]
}
"""

import json
from typing import Any, Dict, List, Optional


def parse_explain_json(raw_json: str) -> Dict[str, Any]:
    data = json.loads(raw_json)
    root_block = data.get("query_block", data)
    children = _parse_block(root_block)
    return {
        "node_type": "ROOT",
        "label": "Query",
        "table_name": None,
        "access_type": None,
        "possible_keys": [],
        "key": None,
        "rows_examined": None,
        "filtered_percent": None,
        "using_filesort": False,
        "using_temporary_table": False,
        "attached_condition": None,
        "children": children,
    }


def _parse_block(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A query_block may contain several kinds of operations layered on
    top of each other (grouping, ordering, dedup) which each wrap an
    inner structure. We peel these off one at a time."""
    nodes: List[Dict[str, Any]] = []

    if not isinstance(block, dict):
        return nodes

    if "ordering_operation" in block:
        inner = block["ordering_operation"]
        node = _wrapper_node(
            "ORDER_BY",
            "Sort (ORDER BY)",
            using_filesort=bool(inner.get("using_filesort", False)),
            using_temporary_table=bool(inner.get("using_temporary_table", False)),
        )
        node["children"] = _parse_block(inner)
        nodes.append(node)
        return nodes

    if "grouping_operation" in block:
        inner = block["grouping_operation"]
        node = _wrapper_node(
            "GROUP_BY",
            "Aggregate (GROUP BY)",
            using_filesort=bool(inner.get("using_filesort", False)),
            using_temporary_table=bool(inner.get("using_temporary_table", False)),
        )
        node["children"] = _parse_block(inner)
        nodes.append(node)
        return nodes

    if "duplicates_removal" in block:
        inner = block["duplicates_removal"]
        node = _wrapper_node(
            "DISTINCT",
            "Remove Duplicates (DISTINCT)",
            using_filesort=bool(inner.get("using_filesort", False)),
            using_temporary_table=bool(inner.get("using_temporary_table", False)),
        )
        node["children"] = _parse_block(inner)
        nodes.append(node)
        return nodes

    if "union_result" in block:
        union = block["union_result"]
        node = _wrapper_node("UNION", "UNION")
        union_children = []
        for spec in union.get("query_specifications", []):
            qb = spec.get("query_block", {})
            union_children.extend(_parse_block(qb))
        node["children"] = union_children
        nodes.append(node)
        return nodes

    if "nested_loop" in block:
        loop_children = []
        for step in block["nested_loop"]:
            loop_children.extend(_parse_block(step))
        node = _wrapper_node("NESTED_LOOP", "Join (Nested Loop)")
        node["children"] = loop_children
        nodes.append(node)
        return nodes

    if "table" in block:
        nodes.append(_table_node(block["table"]))
        return nodes

    if "query_block" in block:
        return _parse_block(block["query_block"])

    return nodes


def _wrapper_node(node_type: str, label: str, using_filesort: bool = False,
                   using_temporary_table: bool = False) -> Dict[str, Any]:
    return {
        "node_type": node_type,
        "label": label,
        "table_name": None,
        "access_type": None,
        "possible_keys": [],
        "key": None,
        "rows_examined": None,
        "filtered_percent": None,
        "using_filesort": using_filesort,
        "using_temporary_table": using_temporary_table,
        "attached_condition": None,
        "children": [],
    }


def _table_node(table: Dict[str, Any]) -> Dict[str, Any]:
    table_name = table.get("table_name")
    access_type = table.get("access_type")
    possible_keys = table.get("possible_keys") or []
    key = table.get("key")
    rows_examined = table.get("rows_examined_per_scan")
    filtered = table.get("filtered")
    try:
        filtered_percent = float(filtered) if filtered is not None else None
    except (TypeError, ValueError):
        filtered_percent = None

    label = f"{table_name or 'derived table'}  ({access_type or 'unknown access'})"

    node = {
        "node_type": "TABLE",
        "label": label,
        "table_name": table_name,
        "access_type": access_type,
        "possible_keys": possible_keys,
        "key": key,
        "rows_examined": rows_examined,
        "filtered_percent": filtered_percent,
        "using_filesort": False,
        "using_temporary_table": False,
        "attached_condition": table.get("attached_condition"),
        "children": [],
    }

    # Correlated / materialized subqueries appear nested inside a table entry
    if "materialized_from_subquery" in table:
        sub_qb = table["materialized_from_subquery"].get("query_block", {})
        node["children"] = _parse_block(sub_qb)

    return node
