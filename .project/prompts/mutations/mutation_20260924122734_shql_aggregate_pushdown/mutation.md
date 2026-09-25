# Mutation Log

## Created
- **tests/storage_fixtures.py** — Shared dataset, in-memory reference stores, throwaway-`mongod` fixture and `stores` fixture (extracted from test_storage_aggregate.py).
- **tests/test_shql_aggregate_pushdown.py** — Engine-level tests on the reference and real Mongo backends: pushdown vs in-memory equivalence, fallbacks, exactness past the candidate cap, `limit: 0`.

## Modified
- **hgai_module_shql/engine.py** — Extracted `_node_filters`/`_edge_filters`; added `_plan_aggregate_pushdown`, `_run_aggregate_pushdown`; `execute_shql` uses storage `aggregate` for eligible queries, skips row fetch when `limit: 0`, adds `meta.aggregate_pushdown`; removed now-unused locals.
- **hgai_module_shql/parser.py** — `limit: 0` is valid when `aggregate` is present.
- **tests/test_storage_aggregate.py** — Now imports shared fixtures; edge fixture flavor changed to `symmetric` and expectations updated.
- **docs/help/notes/shql/shql-advanced.md**, **shql-overview.md**, **docs/help/notes/web-ui/query-screen.md**, **docs/architecture/sparql-vs-shql-gaps.md** — Documented pushdown eligibility, `limit: 0`, `meta.aggregate_pushdown`.
