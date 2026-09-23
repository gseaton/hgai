# Mutation Log

## Modified
- **hgai/api/routers/hypernodes.py** — `GET/PUT/DELETE /graphs/{graph_id}/nodes/{node_id}` changed to `{node_id:path}`.
- **hgai/api/routers/hyperedges.py** — `GET/PUT/DELETE /graphs/{graph_id}/edges/{edge_id}` changed to `{edge_id:path}`.
- **hgai/api/routers/spaces.py** — Space-scoped equivalents (`/spaces/{space_id}/graphs/{graph_id}/nodes/{node_id}` and `.../edges/{edge_id}`, GET/PUT/DELETE each) changed the same way. 12 routes total across the three files.

## Created
- **tests/test_routing_slash_ids.py** — 14 fast, storage-free regression tests using Starlette's own `route.matches()` to assert each of the 12 changed routes correctly matches a path whose id segment contains `/`, extracts the full id (not a truncated prefix) into `path_params`, and that the sibling list/create routes and ordinary slash-free ids are unaffected.
