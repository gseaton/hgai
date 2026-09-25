"""Backend-neutral aggregation: spec validation, semantics, and a reference reducer.

Every storage backend must return the same rows for the same data. This module
is the single statement of those semantics, plus a streaming reducer
(`Accumulator`) that backends without native aggregation inherit through the
default `HypernodeStore.aggregate` / `HyperedgeStore.aggregate`.

Semantics
---------
Field paths      A whitelisted root (`id`, `type`, `label`, `status`, `relation`,
                 `flavor`, `tags`, `hypergraph_id`) or `attributes.<key>[.<key>...]`.
                 Anything else is rejected — paths are never passed to a backend raw.
Missing values   A missing field and an explicit null are the same thing: `None`.
Grouping         Rows are grouped by the tuple of `group_by` values (missing = None).
                 `tags` is unwound: a document counts once per tag, and a document
                 with no tags forms a `None` group. Any other array value groups as a whole.
                 No `group_by` -> exactly one row, even over zero documents.
count            No field: number of documents. With field: number of non-null values.
count_distinct   Number of distinct non-null values.
count_numeric    Number of numeric values (int/float, never bool) — the denominator of `avg`,
                 which lets partial averages from several servers be merged exactly.
sum / avg        Over numeric values only (int/float, never bool); everything else
                 is ignored. `sum` of nothing is 0, `avg` of nothing is None.
min / max        Over non-null values, ordered by `sort_key` (BSON-like: numbers <
                 strings < objects < arrays < booleans < datetimes); None if no values.
Ordering         `order_by`, else ascending by `group_by` paths in order. Nulls sort first.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Tuple

from .filters import AGGREGATE_FUNCTIONS, AggregateMeasure, AggregateSpec

ALLOWED_ROOT_FIELDS = frozenset(
    {"id", "type", "label", "status", "relation", "flavor", "tags", "hypergraph_id"}
)
UNWOUND_FIELDS = frozenset({"tags"})

_ATTR_KEY = r"[A-Za-z0-9_][A-Za-z0-9_:\-]*"
_ATTR_RE = re.compile(rf"^attributes(\.{_ATTR_KEY})+$")
_ALIAS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class AggregateSpecError(ValueError):
    """The AggregateSpec is malformed or references a disallowed field."""


def validate_field_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise AggregateSpecError(f"field path must be a non-empty string, got {path!r}")
    if path in ALLOWED_ROOT_FIELDS or _ATTR_RE.match(path):
        return path
    raise AggregateSpecError(
        f"field path {path!r} is not allowed; use one of {sorted(ALLOWED_ROOT_FIELDS)} "
        f"or attributes.<key>"
    )


def default_alias(m: AggregateMeasure) -> str:
    return m.fn if m.field is None else f"{m.fn}_{m.field.replace('.', '_')}"


def normalise_spec(spec: AggregateSpec) -> AggregateSpec:
    """Validate `spec` and return a copy with aliases and ordering made explicit."""
    group_by = [validate_field_path(p) for p in spec.group_by]
    if len(set(group_by)) != len(group_by):
        raise AggregateSpecError("group_by contains duplicate fields")

    measures: List[AggregateMeasure] = []
    aliases: set = set()
    for m in spec.measures:
        if m.fn not in AGGREGATE_FUNCTIONS:
            raise AggregateSpecError(f"unknown aggregate function {m.fn!r}; use {AGGREGATE_FUNCTIONS}")
        if m.field is None:
            if m.fn != "count":
                raise AggregateSpecError(f"{m.fn} requires a field")
        else:
            validate_field_path(m.field)
        alias = m.alias or default_alias(m)
        if not _ALIAS_RE.match(alias):
            raise AggregateSpecError(f"invalid measure alias {alias!r}")
        if alias in aliases or alias in group_by:
            raise AggregateSpecError(f"duplicate result key {alias!r}")
        aliases.add(alias)
        measures.append(AggregateMeasure(m.fn, m.field, alias))
    if not measures:
        raise AggregateSpecError("at least one measure is required")

    order_by = spec.order_by if spec.order_by is not None else [(p, False) for p in group_by]
    for key, _desc in order_by:
        if key not in aliases and key not in group_by:
            raise AggregateSpecError(f"order_by key {key!r} is not a group_by field or measure alias")

    if spec.limit is not None and spec.limit < 0:
        raise AggregateSpecError("limit must be >= 0")
    return AggregateSpec(group_by, measures, list(order_by), spec.limit)


# ── Value ordering / extraction ───────────────────────────────────────────────

def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def sort_key(v: Any) -> Tuple[int, Any]:
    """Total order over JSON-ish values, mirroring BSON comparison order."""
    if v is None:
        return (0, 0)
    if _is_number(v):
        return (1, v)
    if isinstance(v, str):
        return (2, v)
    if isinstance(v, dict):
        return (3, json.dumps(v, sort_keys=True, default=str))
    if isinstance(v, (list, tuple)):
        return (4, json.dumps(v, default=str))
    if isinstance(v, bool):
        return (5, v)
    if isinstance(v, datetime):
        return (6, v)
    return (7, str(v))


def get_path(doc: Dict[str, Any], path: str) -> Any:
    cur: Any = doc
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def _hashable(v: Any) -> str:
    return json.dumps(v, sort_keys=True, default=str)


# ── Streaming reducer ─────────────────────────────────────────────────────────

class _Cell:
    """Running state of one measure within one group."""

    __slots__ = ("n", "total", "numeric_n", "extreme", "seen")

    def __init__(self) -> None:
        self.n = 0
        self.total: float = 0
        self.numeric_n = 0
        self.extreme: Any = None
        self.seen: Dict[str, Any] = {}


def _feed_value(fn: str, cell: _Cell, v: Any) -> None:
    """Fold one already-extracted field value into a measure's running state."""
    if fn == "count_numeric":
        if _is_number(v):
            cell.n += 1
        return
    if fn in ("sum", "avg"):
        if _is_number(v):
            cell.total += v
            cell.numeric_n += 1
        return
    if v is None:
        return
    if fn == "count":
        cell.n += 1
    elif fn == "count_distinct":
        cell.seen[_hashable(v)] = True
    elif fn in ("min", "max"):
        if cell.extreme is None:
            cell.extreme = v
        else:
            better = sort_key(v) < sort_key(cell.extreme) if fn == "min" \
                else sort_key(v) > sort_key(cell.extreme)
            if better:
                cell.extreme = v


def _final_value(fn: str, cell: _Cell) -> Any:
    if fn in ("count", "count_numeric"):
        return cell.n
    if fn == "count_distinct":
        return len(cell.seen)
    if fn == "sum":
        return cell.total
    if fn == "avg":
        return cell.total / cell.numeric_n if cell.numeric_n else None
    return cell.extreme  # min / max


def reduce_values(fn: str, values: Iterable[Any]) -> Any:
    """Reduce already-extracted values with aggregate function `fn`.

    The same semantics storage backends implement, for callers that hold rows
    in memory (e.g. SHQL's non-pushdown path) — so both paths agree by construction.
    """
    if fn not in AGGREGATE_FUNCTIONS:
        raise AggregateSpecError(f"unknown aggregate function {fn!r}")
    cell = _Cell()
    for v in values:
        _feed_value(fn, cell, v)
    return _final_value(fn, cell)


class Accumulator:
    """Streams documents in, holds O(groups) state, emits rows via `rows()`."""

    def __init__(self, spec: AggregateSpec) -> None:
        self.spec = normalise_spec(spec)
        self._groups: Dict[Tuple[str, ...], Tuple[List[Any], List[_Cell]]] = {}
        if not self.spec.group_by:
            self._groups[()] = ([], [_Cell() for _ in self.spec.measures])

    def _group_values(self, doc: Dict[str, Any]) -> List[List[Any]]:
        """All group-key combinations this doc contributes to (tags unwind)."""
        combos: List[List[Any]] = [[]]
        for path in self.spec.group_by:
            v = get_path(doc, path)
            options = [v]
            if path in UNWOUND_FIELDS:
                options = list(v) if isinstance(v, list) and v else [None]
            combos = [c + [o] for c in combos for o in options]
        return combos

    def add(self, doc: Dict[str, Any]) -> None:
        for values in self._group_values(doc):
            key = tuple(_hashable(v) for v in values)
            entry = self._groups.get(key)
            if entry is None:
                entry = (values, [_Cell() for _ in self.spec.measures])
                self._groups[key] = entry
            for m, cell in zip(self.spec.measures, entry[1]):
                self._feed(m, cell, doc)

    @staticmethod
    def _feed(m: AggregateMeasure, cell: _Cell, doc: Dict[str, Any]) -> None:
        if m.field is None:
            cell.n += 1
            return
        _feed_value(m.fn, cell, get_path(doc, m.field))

    @staticmethod
    def _final(m: AggregateMeasure, cell: _Cell) -> Any:
        return _final_value(m.fn, cell)

    def rows(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for values, cells in self._groups.values():
            row = dict(zip(self.spec.group_by, values))
            for m, cell in zip(self.spec.measures, cells):
                row[m.alias] = self._final(m, cell)
            out.append(row)
        return order_and_limit(out, self.spec)


def order_and_limit(rows: List[Dict[str, Any]], spec: AggregateSpec) -> List[Dict[str, Any]]:
    """Apply a *normalised* spec's ordering and limit (stable, multi-key)."""
    for key, desc in reversed(spec.order_by or []):
        rows.sort(key=lambda r, k=key: sort_key(r.get(k)), reverse=desc)
    return rows if spec.limit is None else rows[: spec.limit]


# ── Default (non-pushdown) execution ──────────────────────────────────────────

DEFAULT_BATCH_SIZE = 1000


async def aggregate_via_search(
    search: Callable[..., Any],
    filters: Any,
    spec: AggregateSpec,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> List[Dict[str, Any]]:
    """Reference aggregation: page through `search(filters, skip, limit)` and reduce.

    Correct for any backend, but transfers every matching document — backends
    override `aggregate` to push the work down. Memory is O(groups), not O(docs).
    Paging assumes `search` returns a stable order for unchanged data.
    """
    acc = Accumulator(spec)
    skip = 0
    while True:
        batch = await search(filters, skip=skip, limit=batch_size)
        for doc in batch:
            acc.add(doc)
        if len(batch) < batch_size:
            break
        skip += batch_size
    return acc.rows()
