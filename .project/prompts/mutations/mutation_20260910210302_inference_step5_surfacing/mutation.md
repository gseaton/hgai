# Mutation Log

## Created
- **hgai/api/routers/inference.py** — New REST router (`/graphs/{graph_id}/infer/...`): `POST .../infer/transitive` (body: `relation`, `start_id`, `end_id?`, `mode`; validates `mode` and the `end_id`-required-for-bool/path rule, delegates to `check_transitive`) and `POST .../infer/expand` (body: `edge_id`; fetches the edge via `engine.get_hyperedge`, delegates to `expand_edge_closure`). Both gated by the existing `require_graph_access("read")` dependency, same as every other graph-scoped route.
- **tests/test_inference.py** — no additions this step (SHQL/MCP/REST wiring is DB- and network-dependent; verified live per this session's established pattern).

## Modified
- **hgai_module_shql/engine.py** — `_eval_edge_pattern()` gains an `infer: bool = False` parameter; when set and a pattern's relation resolves, extends the literal candidate edge list with `expand_edge_closure` results before member-pattern matching runs (so an inferred edge binds `?vars` and chains into later hops exactly like a literal one), and additionally runs `check_transitive` (path mode) when both of a 2-member pattern's endpoints are already concrete (bound variables or literal ids), skipping 1-hop results for the same reason HQL does. `infer` threaded through `_evaluate_patterns` (including its `optional`/`union` recursive branches) from a new top-level `infer: true` SHQL flag, surfaced in the result `meta`.
- **hgai_module_mcp/server.py** — Two new tools: `hgai_infer_expand_edge(graph_id, edge_id)` and `hgai_infer_check_transitive(graph_id, relation, start_id, end_id, mode)`, both thin wrappers delegating to the same `hgai/core/inference.py` functions HQL/SHQL/REST all use. Module docstring's tool-group listing updated (`hgai_infer_*`).
- **hgai/main.py** — Registered the new `inference` router alongside the other API routers.
- **ui/js/app.js** — Added two new entries each to `HQL_EXAMPLES` and `SHQL_EXAMPLES` (inverse-of/symmetric/superproperty expansion, and transitive reachability) so the feature is discoverable from the Query (HQL)/Query (SHQL) screens' existing example-browser panels — no new UI widgetry needed, since both query editors are already free-form YAML/text and `infer: true` is just another field a user can type or copy from an example.

## Explicitly not done this step
- Visualize screen rendering of inferred edges (dashed/dimmed styling with an `_inferred` tooltip) — the plan's own ordering places this last/lowest-priority within Step 5, and it's a materially larger, distinct UI feature (needs a new data-fetching path into the 3D graph's existing node/link rendering pipeline) rather than a natural extension of what else shipped this step. Flagged for a dedicated follow-up.
