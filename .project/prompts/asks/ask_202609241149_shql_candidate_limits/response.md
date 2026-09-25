# Response Summary

## Question / Intent
Identify limits on SHQL query candidate counts that would hinder scaling to millions of nodes/edges, and where those limits are configured.

## Answer / Recommendation
Limits exist and are hard-coded, not configurable:
- `hgai_module_shql/engine.py` ~L375: `hypernodes.search(filters, skip=0, limit=2000)` per node pattern.
- `hgai_module_shql/engine.py` ~L489: `hyperedges.search(filters, skip=0, limit=2000)` per edge pattern.
- `hgai/core/inference.py` ~L406 and ~L652: `hyperedges.search(..., limit=5000)` for inference fact edges (infer: true / materialize).
- `engine.py` ~L1068: user-facing `limit` defaults to 500, applied only after full evaluation, aggregation and ordering (in-memory); it does not raise the 2000 cap.
- `inference.py` `max_depth=10`, `max_iterations=10` bound closure walks.
- `_resolve_node_bindings` does an unbounded `find_by_ids` `$in` over all bound ids.
No env var, settings file or per-query option controls these.

## Key Points
- Overflow past 2000 is silent truncation: count/group_by aggregates are silently wrong.
- Node/edge patterns run one storage search per incoming binding (N+1 shape), joins/filters/order/distinct are in Python memory.
- Already noted in docs/architecture/sparql-vs-shql-gaps.md as a known ceiling.
- Recommended: promote caps to config, surface a `truncated` flag in meta, push aggregation/ordering/limit into storage, batch bound-id lookups.

## Context
Read-only investigation of hgai_module_shql/engine.py, hgai/core/inference.py, hgai_module_storage backend/mongodb stores, and docs.
