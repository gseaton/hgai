# Mutation Summary

## Intent
Let a user export a hypergraph to a file named `hgai-hypergraph-<…>-<…>.export.yml` that another HypergraphAI instance can import, and add import where it didn't exist.

## Context
- Export and import endpoints already existed (`POST /graphs/{id}/export|import`, plus shell commands) but were incomplete for moving a graph between servers: import required the target hypergraph to exist already, so a new instance could not be seeded from a file; it swallowed all errors into a count; export silently stopped at 10,000 nodes/edges; there was no file naming, no YAML download, and nothing in the Web UI.
- Two older export files in the repo root use the same `hgai_export: '1.0'` document shape, so that shape was kept and extended rather than replaced.
- The user's filename template had blanks (`hgai-hypergraph---.export.yml`); it was interpreted as `hgai-hypergraph-<graph-id>-<YYYYMMDDHHMMSS>.export.yml` (UTC timestamp).

## What Changed and Why
- **Format/logic in one place** (`hgai/core/transfer.py`): the same validated document is produced and consumed by the API, shell and UI. Import creates the hypergraph from the file's own `graph` block (`create` mode fails with 409 if it exists; `merge` mode loads into it, creating it if absent, and skips rather than overwrites existing nodes/edges). One bad item is reported (first 25 messages) but doesn't abort the rest.
- **Export completeness** (`engine.export_hypergraph`): pages through all nodes and edges in id order, so large graphs are no longer truncated; adds `exported_at`, `source` server, and `counts`.
- **API**: `GET|POST /graphs/{id}/export?format=yaml` downloads the named file; `POST /graphs/import` accepts the raw file text (so `curl --data-binary @file` works); space-scoped equivalents exist. The old per-graph JSON import endpoints remain and now share the same engine.
- **Clients**: the Hypergraphs screen gets a per-row Export button and an Import dialog (file, optional space, optional new id, create/merge, result summary); the shell's `export`/`import` use the new endpoints.
- **Docs**: README, API reference, and a new help topic (plus cross-links) describe the feature.

## Key Decisions
- **Server-side YAML** rather than parsing YAML in the browser: no new JS dependency, one parser for all clients, and JSON files work too.
- **Server-managed fields are regenerated on import** (timestamps, version, audit trail, hyperkey — which is graph-scoped — and `created_by`); trusting them from a file would forge history.
- **Media references are dropped**, with a count reported, because media files aren't part of an export and would otherwise dangle (and corrupt reference counts) on the target.
- **Merge skips instead of overwriting**, keeping the operation safe and idempotent; replacing a graph means deleting it first.
- **Legacy `/graphs/{id}/import`** was kept for compatibility but now skips duplicates and requires the graph to exist (404 otherwise) instead of silently creating orphans.
- **Permissions** mirror existing behavior: creating an unowned graph needs only a signed-in account (as `POST /graphs` does), merging into an existing one needs write access, and space imports need space membership.
- **Verification**: 26 new unit tests (full suite 241 passed, 2 pre-existing unrelated mesh-ping failures). Live: exported `eden`, imported it under a new id, compared nodes/edges (identical apart from regenerated fields), tested 409, merge-skip, bad/empty/unauthenticated requests, the space variants, a 2,500-node round trip, the UI (export fetch, import dialog, error and merge results, no console errors) and the shell commands. All test graphs/spaces were deleted afterward. A real browser download was not triggered; the export fetch and filename were verified in-page.
