"""SHQL parser and validator."""

import json
from typing import Any, Dict, List

import yaml


class SHQLError(Exception):
    pass


def parse_shql(shql_text: str) -> Dict[str, Any]:
    """Parse SHQL YAML or JSON text into a query dict."""
    try:
        if shql_text.strip().startswith("{"):
            data = json.loads(shql_text)
        else:
            data = yaml.safe_load(shql_text)
    except Exception as e:
        raise SHQLError(f"Failed to parse SHQL: {e}")

    if not isinstance(data, dict):
        raise SHQLError("SHQL must be a YAML/JSON object")

    if "shql" not in data:
        raise SHQLError("SHQL must have a top-level 'shql' key")

    return data["shql"]


def validate_shql(shql: Dict) -> List[str]:
    """Validate an SHQL query dict. Returns a list of error strings."""
    errors = []

    if "from" not in shql:
        errors.append("'from' is required — provide a graph ID or list of graph IDs")

    where = shql.get("where")
    if where is not None and not isinstance(where, list):
        errors.append("'where' must be a list of pattern objects")

    select = shql.get("select")
    if select is not None and not isinstance(select, list):
        errors.append("'select' must be a list of variable expressions")

    limit = shql.get("limit")
    if limit is not None and (not isinstance(limit, int) or limit < 1):
        errors.append("'limit' must be a positive integer")

    offset = shql.get("offset")
    if offset is not None and (not isinstance(offset, int) or offset < 0):
        errors.append("'offset' must be a non-negative integer")

    return errors
