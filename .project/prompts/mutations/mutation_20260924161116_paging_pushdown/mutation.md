# Mutation Log

## Created
- **hgai_module_storage/ordering.py** — Ordered-search semantics: `normalise_order` (whitelist + `id`/`hypergraph_id` tie-breakers), `_Key` comparator with per-key direction, and `search_ordered_via_search` (bounded-memory top-k reference implementation).
- **tests/test_storage_ordering.py** — Conformance suite for `search_ordered` on the reference and real MongoDB backends.
- **tests/test_shql_paging_pushdown.py** — Engine-level equivalence, tiling, cap-exactness, fallback and in-memory-ordering tests.

## Modified
- **hgai_module_storage/backend.py** — `HypernodeStore`/`HyperedgeStore` gain non-abstract `search_ordered` and `supports_ordered_search = False`.
- **hgai_module_storage_mongodb/stores/hypernodes.py**, **hyperedges.py** — Native `search_ordered` (`find().sort().skip().limit()`, allow_disk_use) and `supports_ordered_search = True`.
- **hgai_module_shql/engine.py** — Extracted `_single_pattern` (shared by aggregate and paging planners); added `_plan_paging_pushdown`, `_pushdown_sort_field`, `_run_paging_pushdown`; `execute_shql` fetches sorted pages from storage when eligible, skips in-memory order/slice, and reports `meta.paging_pushdown`. In-memory `order_by` now uses the storage layer's `sort_key` (missing first; fixes TypeError on mixed types).
- **tests/test_shql_aggregate_pushdown.py** — Truncation test split into pushed-down-paging and aggregate-only variants.
- **docs/help/notes/shql/shql-advanced.md**, **docs/help/notes/web-ui/query-screen.md**, **docs/module-development.md** — Documented ordering semantics, paging pushdown, `paging_pushdown`, and the backend `search_ordered` contract.
