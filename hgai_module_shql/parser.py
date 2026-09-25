"""SHQL parser and validator."""

import json
from typing import Any, Dict, List

import yaml


class SHQLError(Exception):
    pass


class SHQLPermissionError(SHQLError):
    """The caller is not permitted to query a graph named by the query."""


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


AGGREGATE_MEASURE_KEYS = ("sum", "avg", "min", "max", "count_numeric")


def _validate_aggregate(aggregate: Any) -> List[str]:
    """Check the `aggregate:` block. `count`/`group_by` keep their historical leniency."""
    if aggregate is None or aggregate == {}:
        return []
    if not isinstance(aggregate, dict):
        return ["'aggregate' must be a mapping (count, group_by, sum, avg, min, max, count_numeric)"]
    errors: List[str] = []
    for key in AGGREGATE_MEASURE_KEYS:
        if key not in aggregate:
            continue
        val = aggregate[key]
        fields = [val] if isinstance(val, str) else val
        if not isinstance(fields, list) or not fields or not all(isinstance(f, str) and f for f in fields):
            errors.append(f"'aggregate.{key}' must be a projected row key or a list of them")
            continue
        for f in fields:
            if f.startswith("?"):
                errors.append(
                    f"'aggregate.{key}': {f!r} must be the projected row key without the leading '?' "
                    f"(e.g. {f[1:]!r})"
                )
    return errors


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
    # `limit: 0` is allowed alongside `aggregate` — "aggregates only, no rows".
    min_limit = 0 if shql.get("aggregate") else 1
    if limit is not None and (not isinstance(limit, int) or limit < min_limit):
        errors.append(
            "'limit' must be a positive integer (0 is allowed only together with 'aggregate')"
            if min_limit == 0 else "'limit' must be a positive integer"
        )

    errors.extend(_validate_aggregate(shql.get("aggregate")))

    offset = shql.get("offset")
    if offset is not None and (not isinstance(offset, int) or offset < 0):
        errors.append("'offset' must be a non-negative integer")

    return errors
