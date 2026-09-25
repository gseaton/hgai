# Response Summary

## Question / Intent
Asked what the plan is for backend-neutral aggregation pushdown in the storage module layer (not just MongoDB).

## Answer / Recommendation
No such plan exists in the repo (only docs/architecture/sparql-vs-shql-gaps.md, which defers server-side aggregation as "a genuine engine change"). Proposed plan:
1. Backend-neutral `AggregateSpec` (group_by fields, measures count/sum/avg/min/max/count_distinct, optional order/limit) and `count`/`aggregate` methods on HypernodeStore/HyperedgeStore in hgai_module_storage/backend.py + filters.py, taking the existing Hypernode/HyperedgeSearchFilters.
2. Non-abstract default implementation in the ABC that pages through `search` and reduces in Python, so every backend is correct on day one; `supports_aggregate_pushdown` capability flag.
3. MongoDB override: factor query building out of `search` into a shared `_build_query`, then `$match` + (`$unwind` for tags) + `$group`, allowDiskUse, index updates in indexes.py.
4. Other backends (SQL GROUP BY, graph DBs) override the same method; a shared conformance suite runs against every backend plus a reference in-memory implementation.
5. SHQL integration: planner pushes down only when the where clause is a single node/edge pattern whose filters are fully expressible in store filters and no infer/federation; otherwise falls back to today's path. Extend `aggregate:` with sum/avg/min/max. Pushed-down aggregates are exempt from candidate caps and never truncated.
6. Later phases: mesh partial-aggregate merge (avg as sum+count), pushdown of order_by/limit, batching the per-binding search.

## Key Points
- Field references must be a validated whitelist grammar (type, relation, tags, attributes.*) to avoid injection into backend queries.
- Must preserve pit, status, SKOS-field stripping semantics.
- infer: true edges are synthesized and cannot be aggregated in storage.
- Multi-pattern joins cannot be pushed down naively.

## Context
Read hgai_module_storage/backend.py, filters.py, mongodb stores/hyperedges.py search, engine aggregate handling, sparql docs.
