# Mutation Log

## Created
- **hgai_module_telemetry/local_storage.py** — `GRAPH_ID = "__local-telemetry"`; `ensure_graph()` (lazy create, race-safe); `build_slug(record)` (the plan's 4-token slug algorithm); `write_records(records)` (writes each as a hypernode via `hgai.core.engine.create_hypernode`) with `_create_with_retry` (disambiguates on a same-second slug collision — see Key Decisions); `prune_older_than(cutoff)` (server-side-filtered repeated-requery deletion via `delete_hypernode`, asserts a real cutoff); `retention_cutoff(days)`; `start_retention_scheduler`/`stop_retention_scheduler`/`_retention_loop` (hourly background sweep, mirrors the mesh scheduler shape).
- **tests/test_telemetry_local_storage.py** — 28 tests against a real throwaway MongoDB (`init_storage`/`close_storage`, not a mock): slug generation, graph lazy-creation and idempotency, written-hypernode shape, real SHQL query + aggregate-pushdown against the graph, the same-second slug collision (a real bug this test suite caught — see below), Hypergraphs-listing and mesh-federation exclusion, permission-model isolation (admin vs. non-admin via the *existing* `check_graph_permission`/`filter_accessible_graphs`), retention (past/future cutoff, `retention_cutoff` disabled-at-zero, `prune_older_than(None)` refused, the scheduler's own sweep), and exporter selection/composition (`CompositeExporter`'s one-fails-other-succeeds and all-fail behavior).

## Modified
- **hgai_module_telemetry/exporters.py** — Added `LocalHypergraphExporter` and `CompositeExporter`; rewrote `select_exporter` per the plan's §2 pseudocode (local storage whenever no usable endpoint, additionally whenever `HGAI_TELEMETRY_LOCAL_ENABLED=true`; an insecure refused endpoint now counts as "no endpoint" rather than hard-`NullExporter`).
- **hgai_module_telemetry/engine.py** — `status()`'s `destination` field describes a `CompositeExporter`'s sub-destinations (`"HTTPExporter+LocalHypergraphExporter"`) instead of just the wrapper's own class name.
- **hgai_module_storage/filters.py** — Added `HypernodeSearchFilters.valid_from_before` (retention sweeps only; distinct from `pit`) and `HypergraphFilters.exclude_system` (hide `__*`-prefixed graphs).
- **hgai_module_storage_mongodb/stores/hypernodes.py**, **hypergraphs.py** — Wired the two new filters into `_build_search_query`/`list`.
- **hgai/core/engine.py** — `list_hypergraphs` gained `include_system: bool = False`, translated to `exclude_system=not include_system`.
- **hgai/api/routers/hypergraphs.py** — `GET /api/v1/graphs` gained an `include_system` query parameter.
- **hgai_module_mesh/engine.py** — `_local_graph_ids()` (the mesh federation "every graph on this server" fan-out) now excludes system graphs.
- **hgai/main.py** — Wires `start_retention_scheduler`/`stop_retention_scheduler` into the lifespan alongside the existing telemetry export task.
- **hgai/config.py**, **.env.example** — `telemetry_local_enabled`/`telemetry_local_retention_days` descriptions updated from "reserved for Phase 3a" to their real behavior.
- **tests/test_telemetry.py** — Two Phase 1 tests updated for the new `select_exporter` default (no endpoint now means local storage, not `NullExporter`).
