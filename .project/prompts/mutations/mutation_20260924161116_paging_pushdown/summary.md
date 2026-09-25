# Mutation Summary

## Intent
Phase 4: have the storage layer sort and page rows (`order_by`, `offset`, `limit`) for single-pattern SHQL queries, so result pages are exact on large graphs rather than sorted from a capped candidate fetch.

## Context
Phases 1-3 added storage aggregation and SHQL aggregate pushdown. Row retrieval still fetched up to the candidate cap, sorted in Python and sliced.

## What Changed and Why
A new `search_ordered` store method (default: bounded-memory top-k over `search`; MongoDB: native sort) defines one ordering everywhere: missing first, BSON-like type order, per-key direction, deterministic `id`/`hypergraph_id` tie-breaks so `skip`/`limit` pages tile exactly. The SHQL planner shares a `_single_pattern` analysis with aggregate pushdown, and a query is paged in storage when the pattern binds a variable, every `order_by` key is a projected scalar field of it (or the whole variable is projected), and any aggregate is already storage-computed. Rows are then projected exactly like the in-memory path. `meta.paging_pushdown` reports which path ran. Without `order_by`, plain `search(skip, limit)` is used so no backend scans everything for a simple page.

## Key Decisions
- In-memory `order_by` was switched to the storage layer's `sort_key`, so both paths agree by construction; it also fixes a latent TypeError when a column mixes numbers and text (and missing values previously became `""`).
- Ties: storage breaks by id, in-memory keeps natural order — documented; tests avoid ambiguous ties or use ties whose natural order equals id order.
- Non-native backends get the exact-but-scanning default for ordered queries (consistent with aggregates); unordered paging never scans.
- Queries with in-memory aggregates skip paging pushdown, since the aggregate needs all rows.
- Federated (dot_items) queries, infer, distinct, joins, filters, tags ordering all fall back.
