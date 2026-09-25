# Mutation Log

## Created
None (capture files aside).

## Modified
- **hgai/config.py** — Added `shql_max_node_candidates` (2000), `shql_max_edge_candidates` (2000), `inference_max_fact_edges` (5000) settings (env `HGAI_*`).
- **hgai_module_shql/engine.py** — Added `_search_capped` (fetches cap+1, trims, records truncation); node/edge pattern searches use it with settings. `execute` installs a truncation sink and adds `meta.truncated` / `meta.truncated_by`.
- **hgai/core/inference.py** — Added `truncation_sink` ContextVar, `note_truncation`, `fetch_fact_edges`; both 5000 limits now use the setting; `project_inference` returns `truncated`/`truncated_by`.
- **tests/test_shql.py** — Added parametrized test for cap boundary and truncation flag.
- **README.md**, **docs/help/notes/admin/configuration.md**, **.env.example** — Documented the three new env vars.
- **docs/help/notes/web-ui/query-screen.md**, **docs/architecture/sparql-vs-shql-gaps.md** — Updated to describe configurable caps and `meta.truncated`.
