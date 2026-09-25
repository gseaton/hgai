# Mutation Summary

## Intent
Phase 6: make `aggregate:` correct over federated (mesh) queries. Previously each remote server's aggregate meta was discarded and the caller re-aggregated the merged, per-server-paged rows, so results were incomplete past the row limits and skipped storage pushdown.

## Context
Phases 1-5 built exact storage-side aggregation, sorting/paging and batched joins for a single server. Federation (`hgai_module_mesh`) fans a rewritten query to each server and concatenates items.

## What Changed and Why
Every server now aggregates its own graphs and returns meta; the caller aggregates its local graphs separately (storage pushdown is allowed again) and merges all partials with `merge_aggregate_meta`: counts/sums add, min/max use the storage sort order, groups are unioned, and `avg` is merged sum / merged numeric count. Since avg is not decomposable, remote queries are widened with `sum` and `count_numeric` for every averaged field; that required a new storage aggregate function, `count_numeric`, implemented in the spec/reducer/Mongo pipeline and conformance-tested. Merging only exposes the keys the user asked for. Results report `meta.federation` (servers, errors, whether merged), propagate remote truncation, and set `aggregate_pushdown` only if all servers used storage.

## Key Decisions
- Graceful degradation: if any partial lacks what the merge needs (older server) or the query uses `distinct`, aggregation falls back to the merged rows exactly as before.
- Failed servers are excluded from rows and aggregates and reported in `meta.federation.errors`.
- Rows behaviour is unchanged (per-server pages still concatenated); only aggregates changed.
- Row paging pushdown stays disabled for federated queries (rows from several servers must be merged).
- The direct mesh API (`federated_shql`) also returns the merged `aggregate`.
- Tests use real engine runs for remotes (serialised behind a lock because the module-level storage accessor is patched) and an oracle computed over the union of all servers' rows.
