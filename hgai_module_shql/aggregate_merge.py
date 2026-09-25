"""Merging SHQL `aggregate:` results computed independently on several servers.

A federated query runs on every mesh server, and each returns its own
`meta` (`count`, `sum`/`avg`/`min`/`max`/`count_numeric`, `groups`,
`group_measures`). Those partials combine exactly, provided each server also
reports what the combination needs:

    count, sum, count_numeric   add
    min, max                    min / max under the storage layer's `sort_key`
    avg                         merged sum / merged count_numeric

`avg` is the only measure that is not directly decomposable, so a query sent
to a server is first widened with `partial_aggregate` (adding `sum` and
`count_numeric` for every `avg` field). `merge_aggregate_meta` then returns
exactly the keys the *original* aggregate asked for, or None when any part is
missing what it needs (for example an older server) — the caller then falls
back to aggregating the merged rows.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from hgai_module_storage.aggregate import sort_key

MEASURE_FNS = ("sum", "avg", "min", "max", "count_numeric")


def measure_requests(aggregate: Dict[str, Any]) -> List[Tuple[str, str]]:
    """The (fn, projected-row-key) pairs requested by measure keys, de-duplicated."""
    pairs: List[Tuple[str, str]] = []
    for fn in MEASURE_FNS:
        val = aggregate.get(fn)
        if val is None:
            continue
        for key in ([val] if isinstance(val, str) else list(val)):
            if (fn, key) not in pairs:
                pairs.append((fn, key))
    return pairs


def partial_aggregate(aggregate: Dict[str, Any]) -> Dict[str, Any]:
    """`aggregate` widened so each server also reports what merging `avg` needs."""
    pairs = measure_requests(aggregate)
    avg_keys = [k for fn, k in pairs if fn == "avg"]
    if not avg_keys:
        return aggregate
    widened = dict(aggregate)
    for fn in ("sum", "count_numeric"):
        have = [k for f, k in pairs if f == fn]
        widened[fn] = have + [k for k in avg_keys if k not in have]
    return widened


def _merge_measure(fn: str, key: str, sources: List[Dict[str, Dict[str, Any]]]) -> Any:
    """Merge one (fn, key) over `sources`, each shaped `{fn: {key: value}}`."""
    if fn == "avg":
        total = _merge_measure("sum", key, sources)
        n = _merge_measure("count_numeric", key, sources)
        return total / n if n else None
    values = [src[fn][key] for src in sources]          # KeyError => a part can't be merged
    if fn in ("sum", "count_numeric"):
        return sum(values)
    present = [v for v in values if v is not None]      # min / max
    if not present:
        return None
    return min(present, key=sort_key) if fn == "min" else max(present, key=sort_key)


def merge_aggregate_meta(parts: List[Dict[str, Any]], aggregate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Merge per-server aggregate `meta` dicts into the result for `aggregate`.

    `parts` must have been produced for `partial_aggregate(aggregate)`.
    Returns None if any part lacks a value the merge needs.
    """
    pairs = measure_requests(aggregate)
    out: Dict[str, Any] = {}
    try:
        if "count" in aggregate:
            out["count"] = sum(p["count"] for p in parts)
        for fn, key in pairs:
            out.setdefault(fn, {})[key] = _merge_measure(fn, key, parts)

        if "group_by" in aggregate:
            groups: Dict[str, int] = {}
            members: Dict[str, List[Dict[str, Any]]] = {}     # group -> parts that have it
            for p in parts:
                for group, n in p["groups"].items():
                    groups[group] = groups.get(group, 0) + n
                    if pairs:
                        members.setdefault(group, []).append(p["group_measures"][group])
            out["groups"] = groups
            if pairs:
                out["group_measures"] = {
                    group: _shape((fn, key, _merge_measure(fn, key, srcs)) for fn, key in pairs)
                    for group, srcs in members.items()
                }
    except (KeyError, TypeError, AttributeError):
        return None
    return out


def _shape(triples: Iterable[Tuple[str, str, Any]]) -> Dict[str, Dict[str, Any]]:
    shaped: Dict[str, Dict[str, Any]] = {}
    for fn, key, value in triples:
        shaped.setdefault(fn, {})[key] = value
    return shaped
