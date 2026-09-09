# Response Summary

## Question / Intent
The user wanted to understand exactly how HypergraphAI's dedup/uniqueness mechanism works for hypernodes and hyperedges (which fields feed the hash, and how it's enforced), and then wanted a design for the specific change needed to let two hyperedges share the same flavor, relation, and members but have different `valid_from`/`valid_to` windows (e.g. the same Three Stooges lineup — moe, larry, shemp — being valid during two separate historical periods).

## Answer / Recommendation

**Current mechanism:**
- Hypernodes have no hashing at all — dedup is purely the caller-supplied `id`, enforced by an app-level 409 pre-check (`hgai/api/routers/hypernodes.py:54`) plus a DB-level unique compound index on `(id, hypergraph_id)` (`hgai_module_storage_mongodb/indexes.py:43-47`).
- Hyperedges use a computed "hyperkey": `generate_hyperkey()` (`hgai/core/engine.py:31-42`) hashes `{relation: lower/stripped, graph: hypergraph_id, members: sorted(member_node_ids)}` via SHA-256, truncated to 32 hex chars. If no explicit `id` is supplied, the hyperkey becomes the `id` (`engine.py:254-269`). Two unique compound indexes back this: `(id, hypergraph_id)` and `(hyperkey, hypergraph_id)` (`hgai_module_storage_mongodb/indexes.py:66-74`) — the second means even a distinct custom `id` is rejected if the computed hyperkey collides. `update_hyperedge()` (`engine.py:318-324`) recomputes the hyperkey on every save.
- Fields NOT in the hash: `flavor`, `valid_from`, `valid_to`, `label`, `tags`, `attributes`, media, skos_* fields.
- Rough edge found during investigation: the router only pre-checks the `id` half (`hyperedges.py:58-63`), not the hyperkey — a hyperkey collision today surfaces as a raw, uncaught pymongo `DuplicateKeyError` (~500) instead of a clean 409. The bulk importer (`engine.py:425-435`) additionally swallows this into a generic `errors` counter.

**Why the two-lineups scenario fails today:** since `valid_from`/`valid_to` aren't part of the hash, two hyperedges with identical relation+members (regardless of date range) hash identically — the first insert succeeds, the second is rejected by the `hyperkey_graph_unique` index no matter what `id` is given.

**Recommended fix:**
1. Extend `generate_hyperkey()` to accept and hash `valid_from`/`valid_to` (canonically serialized, e.g. UTC `.isoformat()`, with a `None`/`null` sentinel — not empty string — for unbounded).
2. Update both call sites — `create_hyperedge()` (`engine.py:256`) and the hyperkey-recompute block in `update_hyperedge()` (`engine.py:318-324`, which needs the same dumped-vs-existing fallback pattern already used for relation/members, added for the two date fields).
3. No index/schema change needed — the existing `(hyperkey, hypergraph_id)` unique index automatically does the right thing once the hash reflects the temporal window.
4. Add the missing app-level pre-check for hyperkey collisions in `create_edge()` so it raises a clean 409 instead of a raw DB error.
5. Leave `flavor` out of the hash, matching the user's example (same flavor, different dates = same "kind of fact," different time). Noted this could be extended the same way if flavor-level distinctness is ever wanted too.

## Key Points
- Two side effects flagged (not implemented): (a) since the hash is recomputed on every update, editing an edge's dates changes its identity hash going forward — correct behavior, but means the edit only succeeds if no other edge already has that exact resulting window; (b) hash-based uniqueness only blocks *exact* duplicate windows, not *overlapping* windows (e.g. 1959–1962 vs 1960–1961) — that needs a separate application-level interval-overlap check, which is a distinct feature from what's needed to satisfy the user's stated scenario.
- No code changes were made in this turn — this was a design/explanation request. The user was asked whether to proceed with implementation.

## Context
Investigation touched: `hgai/core/engine.py` (generate_hyperkey, create_hyperedge, update_hyperedge, import_hypergraph_data), `hgai_module_storage_mongodb/indexes.py` (all unique index definitions), `hgai_module_storage_mongodb/stores/hyperedges.py` (create/get_by_id_or_hyperkey), `hgai/models/hyperedge.py` (field list confirming what's excluded from the hash), `hgai/api/routers/hyperedges.py` and `hypernodes.py` (409 pre-check behavior).
