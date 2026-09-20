# Mutation Log

## Created
- **hgai/core/transfer.py** — Export-file logic: `export_filename` (`hgai-hypergraph-<id>-<YYYYMMDDHHMMSS>.export.yml`), `dump_yaml`, `validate_export`/`parse_export` (YAML or JSON, version check), and `import_document` (creates the hypergraph from the file's definition; `create`/`merge` modes; skips existing items; per-item error reporting; drops server-managed fields and media references).
- **hgai/api/transfer_http.py** — Shared HTTP glue: YAML attachment response with `Content-Disposition`, raw-body reader (100 MB cap), and error mapping (400/404/409).
- **tests/test_transfer.py** — 26 tests: filename, YAML/JSON round trip, invalid-file rejection, the repo's older export files still parse, create/merge/skip/duplicate-edge/override/space handling, error capping.
- **docs/help/notes/web-ui/export-import.md** — Help topic (`help-export-import`) covering the file format, UI, shell and REST usage.

## Modified
- **hgai/core/engine.py** — `export_hypergraph` now pages through every node/edge (was capped at 10,000 each), adds `exported_at`/`source`/`counts` metadata, puts identifying keys first and emits JSON-safe values; `import_hypergraph_data` now delegates to `transfer.import_document` (merge into an existing graph).
- **hgai/api/routers/hypergraphs.py** — `/graphs/{id}/export` accepts GET and POST with `?format=json|yaml`; new `POST /graphs/import` (raw YAML/JSON body, `graph_id`, `mode`); legacy `POST /graphs/{id}/import` validates input and returns the richer result.
- **hgai/api/routers/spaces.py** — Same export options for space graphs; new `POST /spaces/{space_id}/graphs/import`; legacy per-graph import updated.
- **shell/hgai_shell.py** — `export` writes the timestamped `.export.yml` by default (or `-o`); `import -f` creates a hypergraph from the file (`-g` renames, `--merge` merges); new client methods for the raw endpoints.
- **ui/index.html** — Import button on the Hypergraphs screen and the Import Hypergraph modal.
- **ui/js/api.js** — `downloadGraphExport` and `importGraphFile` (authenticated raw-file fetches).
- **ui/js/app.js** — Export button per row (browser download), import modal logic (file peek, space/id/mode, result summary); `_populateSpaceSelect` takes an optional select id.
- **README.md**, **docs/api-reference.md** — Documented the export/import endpoints, file format, shell commands and Web UI.
- **docs/help/notes/{home,concepts/hypergraphs,admin/backup,integration/rest-api,integration/shell,reference/faq,reference/glossary,web-ui/web-ui-tour}.md** — Links to and mentions of the new export/import topic.
