# Mutation Summary

## Intent
Phase 2 of storage-layer aggregation: make SHQL `aggregate: {count, group_by}` be answered by the storage layer (built in phase 1) for simple queries, so results are exact and not limited by the candidate caps.

## Context
Phase 1 added `aggregate()`/`count()` to the node/edge stores. In-memory aggregation counted only the ≤cap fetched rows and silently undercounted on large graphs.

## What Changed and Why
A planner (`_plan_aggregate_pushdown`) accepts a query only when it can prove storage returns the same `count`/`groups` as the in-memory path: one node/edge pattern with literal constraints, no filters/optional/union/members/distinct/infer, no federated rows, and a `group_by` that is a projected, scalar field of the pattern's own variable. Everything else falls back unchanged. Filter construction was extracted into `_node_filters`/`_edge_filters` so matching and pushdown cannot build different queries. Results carry `meta.aggregate_pushdown`. `limit: 0` (now valid with `aggregate`) skips the row fetch entirely, which is what makes count-only queries cheap on huge graphs.

## Key Decisions
- Equivalence is enforced by tests that run each query with and without the planner on both a reference backend and real MongoDB.
- `tags` group_by falls back (storage unwinds arrays; in-memory groups by whole list).
- Group keys use `str(value)` with missing → "None" to match in-memory output.
- Pushdown is used even for backends without native aggregation (default reducer is exact but scans everything) — exactness preferred over silently wrong answers.
- When `limit > 0`, `items` still come from the capped fetch, so `meta.truncated` continues to describe items only.
- sum/avg/min/max in `aggregate:` deliberately left for phase 3.
