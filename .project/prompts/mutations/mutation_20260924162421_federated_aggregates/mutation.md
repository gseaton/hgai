# Mutation Log

## Created
- **hgai_module_shql/aggregate_merge.py** — `measure_requests`, `partial_aggregate` (widens `avg` with `sum` + `count_numeric`), `merge_aggregate_meta` (exact merge of per-server aggregate meta; None if a part lacks what is needed).
- **tests/test_shql_federated_aggregates.py** — Federated aggregate tests: real `execute_shql` remotes behind a fake HTTP client compared against a union oracle; failed server, server without partials, `distinct`, rows still merged, canned-remote truncation/pure-remote/direct-API cases, merge unit tests.

## Modified
- **hgai_module_storage/filters.py**, **aggregate.py**, **hgai_module_storage_mongodb/aggregation.py** — New aggregate function `count_numeric` (count of numeric, non-bool values) in the spec, reference reducer and Mongo pipeline (`$isNumber`).
- **hgai_module_shql/parser.py** — `count_numeric` accepted/validated as a measure key.
- **hgai_module_shql/engine.py** — Uses shared `measure_requests`; `execute_shql` collects federated partials/errors, aggregates the local portion separately (pushdown allowed when federated), merges with remote partials, falls back to merged rows if a partial is missing or `distinct`; row paging pushdown gated on `not federated`; new `meta.federation`, propagated truncation, `aggregate_pushdown` across servers.
- **hgai_module_mesh/engine.py** — `_rewrite_from` widens `aggregate:` for remote servers; `_query_server` returns server `meta`; `execute_dot_refs`/`federated_shql` return `partials`; `federated_shql` returns merged `aggregate`; new `merged_aggregate`.
- **tests/test_storage_aggregate.py** — `count_numeric` coverage.
- **docs/help/notes/admin/meshes.md**, **docs/help/notes/shql/shql-advanced.md**, **docs/module-development.md**, **docs/architecture/sparql-to-shql-conversion-plan.md** — Documented federated aggregates, `count_numeric`, `meta.federation`.
