# Mutation Log

## Modified
- **hgai_module_shql/engine.py** — `_eval_edge_pattern` now reads and honors a pattern's `id:` key. Added `edge_id = pattern.get("id")` extraction; extended the "already bound" fast path to also reject a binding whose existing edge doc's `id` doesn't match a resolved `id:` constraint; added resolution of `edge_id` (literal or `?var`, via `_resolve_var`, mirroring the existing node-pattern `id` handling) before the search, skipping the binding entirely if a variable reference can't be resolved; and passed the resolved id through to `HyperedgeSearchFilters(extra_filters={"id": resolved_id})` so it's actually applied as a MongoDB query filter (reusing the same `extra_filters` pass-through mechanism already used for boolean operators like `$or`).
- **README.md** — Added `id: my-edge-id       # match by exact edge id (literal or ?var)` to the documented `### Edge Pattern` example, reflecting the new capability.
