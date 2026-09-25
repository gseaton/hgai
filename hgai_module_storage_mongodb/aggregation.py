"""Translate a backend-neutral AggregateSpec into a MongoDB aggregation pipeline.

Semantics are defined in `hgai_module_storage.aggregate`; this module only maps
them onto `$match` / `$unwind` / `$group` / `$sort` / `$limit`. Field paths are
validated by `normalise_spec` before they are interpolated, and internal
`g<i>` / `m<i>` names stand in for user paths/aliases inside the pipeline.
"""

from typing import Any, Dict, List

from hgai_module_storage.aggregate import UNWOUND_FIELDS, normalise_spec
from hgai_module_storage.filters import AggregateSpec


def _accumulator(fn: str, field: str | None) -> Dict[str, Any]:
    if field is None:
        return {"$sum": 1}
    ref = f"${field}"
    if fn == "count":
        return {"$sum": {"$cond": [{"$ne": [{"$ifNull": [ref, None]}, None]}, 1, 0]}}
    if fn == "count_numeric":
        return {"$sum": {"$cond": [{"$isNumber": ref}, 1, 0]}}
    if fn == "count_distinct":
        return {"$addToSet": ref}
    return {f"${fn}": ref}  # sum / avg / min / max


async def run_aggregate(collection, query: Dict[str, Any], spec: AggregateSpec) -> List[Dict[str, Any]]:
    spec = normalise_spec(spec)
    pipeline: List[Dict[str, Any]] = [{"$match": query}]

    for path in spec.group_by:
        if path in UNWOUND_FIELDS:
            pipeline.append({"$unwind": {"path": f"${path}", "preserveNullAndEmptyArrays": True}})

    group: Dict[str, Any] = {
        "_id": {f"g{i}": f"${p}" for i, p in enumerate(spec.group_by)} or None,
    }
    for j, m in enumerate(spec.measures):
        group[f"m{j}"] = _accumulator(m.fn, m.field)
    pipeline.append({"$group": group})

    distinct = {
        f"m{j}": {"$size": {"$setDifference": [f"$m{j}", [None]]}}
        for j, m in enumerate(spec.measures) if m.fn == "count_distinct"
    }
    if distinct:
        pipeline.append({"$set": distinct})

    def internal(key: str) -> str:
        if key in spec.group_by:
            return f"_id.g{spec.group_by.index(key)}"
        return f"m{[m.alias for m in spec.measures].index(key)}"

    if spec.order_by:
        pipeline.append({"$sort": {internal(k): -1 if desc else 1 for k, desc in spec.order_by}})
    if spec.limit is not None:
        pipeline.append({"$limit": spec.limit})

    rows: List[Dict[str, Any]] = []
    async for doc in collection.aggregate(pipeline, allowDiskUse=True):
        row: Dict[str, Any] = {}
        ident = doc.get("_id") or {}
        for i, p in enumerate(spec.group_by):
            row[p] = ident.get(f"g{i}")
        for j, m in enumerate(spec.measures):
            row[m.alias] = doc.get(f"m{j}")
        rows.append(row)

    if not spec.group_by and not rows and spec.limit != 0:
        # $group over zero documents yields nothing; the contract says one row.
        empty = {"count": 0, "count_distinct": 0, "sum": 0}
        rows.append({m.alias: empty.get(m.fn) for m in spec.measures})
    return rows
