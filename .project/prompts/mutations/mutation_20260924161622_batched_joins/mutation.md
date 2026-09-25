# Mutation Log

## Created
- **tests/test_shql_join_batching.py** — Join tests on the reference and real MongoDB backends: result/order independence from batch size, query-count assertions, cap and fallback behaviour, chunked variable resolution.

## Modified
- **hgai_module_shql/engine.py** — `_eval_node_pattern` / `_eval_edge_pattern` now classify bindings into distinct search keys, fetch each once (`_fetch_node_docs`, `_fetch_edge_docs`, batched by `shql_join_batch_size`, exact per-key fallback when a batch may have hit the cap), then expand in binding order. Added `_bound_member_ids`, `_chunks`; `_edge_filters` accepts `member_node_ids_any`; `_resolve_node_bindings` chunks `find_by_ids` (`_RESOLVE_CHUNK`).
- **hgai/config.py** — Added `shql_join_batch_size` (default 200).
- **tests/storage_fixtures.py** — Edges now have members; reference stores honour node_ids_in/tags/attributes/flavor/member filters/edge id, count searches, and implement `find_by_ids`.
- **README.md**, **docs/help/notes/admin/configuration.md**, **.env.example** — Documented `HGAI_SHQL_JOIN_BATCH_SIZE`.
- **docs/help/notes/shql/shql-advanced.md** — Added "Joins over many matches".
