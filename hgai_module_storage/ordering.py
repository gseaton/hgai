"""Backend-neutral ordered search: order specs, semantics, and a reference implementation.

`HypernodeStore.search_ordered` / `HyperedgeStore.search_ordered` return one page
of matching documents sorted by `order_by`. Every backend must agree on:

Field paths   Same whitelist as aggregation (`validate_field_path`).
Value order   `hgai_module_storage.aggregate.sort_key`: missing/null first, then
              numbers < strings < objects < arrays < booleans < datetimes.
Direction     Per key; descending is the exact reverse of ascending.
Tie-breaking  Rows equal on every key are ordered by `id`, then `hypergraph_id`
              (ascending), so `skip`/`limit` pages are deterministic and
              never overlap or skip a row.
"""

from __future__ import annotations

import heapq
from typing import Any, Callable, Dict, List, Sequence, Tuple

from .aggregate import AggregateSpecError, get_path, sort_key, validate_field_path

OrderBy = Sequence[Tuple[str, bool]]   # (field path, descending)

TIE_BREAKERS: Tuple[Tuple[str, bool], ...] = (("id", False), ("hypergraph_id", False))
DEFAULT_BATCH_SIZE = 1000


def normalise_order(order_by: OrderBy) -> List[Tuple[str, bool]]:
    """Validate `order_by` and append the deterministic tie-breakers."""
    out: List[Tuple[str, bool]] = []
    seen = set()
    for path, desc in order_by:
        validate_field_path(path)
        if path in seen:
            raise AggregateSpecError(f"order_by contains duplicate field {path!r}")
        seen.add(path)
        out.append((path, bool(desc)))
    out.extend(t for t in TIE_BREAKERS if t[0] not in seen)
    return out


class _Key:
    """Sort key with independent per-field direction."""

    __slots__ = ("parts",)

    def __init__(self, doc: Dict[str, Any], order: List[Tuple[str, bool]]):
        self.parts = [(sort_key(get_path(doc, p)), d) for p, d in order]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Key) and [a for a, _ in self.parts] == [b for b, _ in other.parts]

    __hash__ = None  # type: ignore[assignment]

    def __lt__(self, other: "_Key") -> bool:
        for (a, desc), (b, _) in zip(self.parts, other.parts):
            if a != b:
                return (a > b) if desc else (a < b)
        return False


async def search_ordered_via_search(
    search: Callable[..., Any],
    filters: Any,
    order_by: OrderBy,
    skip: int = 0,
    limit: int = 500,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> List[Dict[str, Any]]:
    """Reference ordered search: stream every match through `search`, keep the best skip+limit.

    Correct on any backend but scans all matching documents; memory is
    O(skip + limit). Backends override `search_ordered` to sort natively.
    """
    order = normalise_order(order_by)
    keep = skip + limit
    if limit <= 0:
        return []
    heap_items: List[Tuple[_Key, int, Dict[str, Any]]] = []
    counter = 0
    offset = 0
    while True:
        batch = await search(filters, skip=offset, limit=batch_size)
        for doc in batch:
            heap_items.append((_Key(doc, order), counter, doc))
            counter += 1
        # Trim periodically so memory stays bounded by ~keep + batch_size.
        if len(heap_items) > 2 * max(keep, batch_size):
            heap_items = heapq.nsmallest(keep, heap_items, key=lambda t: (t[0], t[1]))
        if len(batch) < batch_size:
            break
        offset += batch_size
    best = heapq.nsmallest(keep, heap_items, key=lambda t: (t[0], t[1]))
    return [doc for _k, _i, doc in best[skip:]]
