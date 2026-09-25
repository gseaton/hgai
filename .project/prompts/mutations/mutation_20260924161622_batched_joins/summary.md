# Mutation Summary

## Intent
Phase 5: remove the N+1 query pattern in SHQL joins, where each node/edge pattern ran one storage search per incoming binding.

## Context
Earlier phases moved aggregation and sorting/paging into storage for single-pattern queries. Multi-pattern joins still cost one query per binding per pattern, and repeated identical searches when the filter did not depend on the binding.

## What Changed and Why
Pattern evaluation is now three phases: (1) classify bindings and reduce them to distinct search keys (a resolved node id; relation + already-bound member-id set + edge id); (2) fetch each distinct key once, batching keys that differ only by id/member set into one `any-of` query (node_ids_in, member_node_ids_any) of up to `HGAI_SHQL_JOIN_BATCH_SIZE` keys; (3) expand documents back onto bindings in the original order. Documents are shared between bindings with the same key. Identical-filter patterns (e.g. cross joins) collapse to a single query. `find_by_ids` for variable resolution is chunked.

## Key Decisions
- Exactness first: an edge batch fetches at most `cap * keys + 1` documents; hitting that limit means a key may be missing edges, so that chunk is redone key by key with the original queries. Per-key results are truncated to the cap and reported through the existing truncation sink, so results and `meta.truncated` match one-query-per-binding.
- Node id lookups need no cap: (id, hypergraph_id) is unique so the batch limit is exact.
- Batch size 1 reproduces the original per-key queries, which the tests use as the reference behaviour.
- Edge-id variables and relation variables are grouped, not batched across values (rare; keeps the storage filter surface unchanged).
- No storage interface change: batching uses existing `HyperedgeSearchFilters.member_node_ids_any` and `HypernodeSearchFilters.node_ids_in`.
