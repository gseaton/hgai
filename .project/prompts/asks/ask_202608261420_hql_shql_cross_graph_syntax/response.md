# Response Summary

## Question / Intent
The user wanted the exact syntax, in both HQL and SHQL, for a query's `from:` clause to reference hypernodes/hyperedges living in a different graph, a different space (space-scoped graph), or a remote graph/space reached through a mesh.

## Answer / Recommendation
HQL and SHQL use **byte-for-byte identical `from:` syntax** — both engines run near-duplicate resolution logic (`hgai_module_hql/engine.py:254-353` and `hgai_module_shql/engine.py:901-966`: same dot-count partitioning, same slash-split for space-scoping, same bare-mesh-id federation redirect, same logical-graph `composition` expansion). The only difference between the two languages is the query body shape (HQL's `match`/`where` filter dict vs SHQL's `where:` pattern list with `?var` bindings) — never the `from:` syntax itself.

| Scope | Syntax | Verbatim example (from README.md / docs/concepts.md) |
|---|---|---|
| Same-server, other graph | bare `graph_id` | `from: my-graph` |
| List of graphs | YAML list | `from:`<br>`  - hello-world`<br>`  - alpha/alpha-hg` |
| Space-scoped graph | `space_id/graph_id` (slash separator) | `from: alpha/alpha-hg` |
| Logical graph (transparent union) | bare id of a `type: logical` hypergraph — auto-expands its `composition: [...]` list | `from: my-logical-graph` |
| Mesh remote graph (unowned) | 3-component dot-notation: `mesh_id.server_id.graph_id` | `from: abc.srv1.alpha` |
| Mesh remote graph (space-scoped) | 4-component dot-notation: `mesh_id.server_id.space_id.graph_id` | `from: my-mesh.remote-server.alpha.alpha-hg` |
| Mesh wildcards | `*` in any dot position | `abc.*.alpha` (all servers with graph `alpha`), `abc.srv1.*` (all graphs on one server), `abc.*.*` (everything in the mesh) |
| Bare mesh-wide federation | bare `mesh_id`, no dots — queries every server in the mesh concurrently and merges results | `from: alpha-bravo-mesh` |
| Mixed list | local ids and mesh dot-refs combined in one list | `from:`<br>`  - local-graph`<br>`  - my-mesh.server-a.remote-graph`<br>`  - my-mesh.*.shared-graph` |

## Key Points
- **Test coverage differs by form** — same-server graph refs (`from: graph-id`) and bare mesh-wide federation (`from: mesh-id`) are both directly exercised by real tests (`tests/test_query.py:10,31`; `tests/test_mesh.py::test_federated_hql_merges_results`). Space-scoped refs (`from: space/graph`) and mesh dot-notation (`from: mesh.server[.space].graph`) are implemented and match their documented `README.md` examples exactly in the engine code, but **no test in the repo exercises either form** — they should be treated as "should work per the code," not "verified to work," until covered.
- Disambiguation is purely dot-count-based: `graph_id`, `space_id`, `mesh_id`, and `server_id` are all forbidden from containing `.` (enforced at the model layer, `hgai/models/hypergraph.py:32-36`, `hgai_module_mesh/models.py:16-20,33-37`) specifically so the parser can split unambiguously — 2 dots means a 3-component unowned mesh ref, 3 dots means a 4-component space-scoped mesh ref.
- Mesh fan-out (wildcards or bare mesh-wide federation) runs every targeted server concurrently via `asyncio.gather` — total latency is bounded by the slowest server, not the sum.
- Each row returned from a mesh server carries an injected `_mesh_server_id` field so the origin server of any given result can be identified.
- The "mixed list" case (local ids alongside mesh dot-refs in the same `from:` list) has no dedicated SHQL example in the docs, but the code path that handles it (`hgai_module_hql/engine.py:309-310`, `hgai_module_shql/engine.py:916-917`) is identical to HQL's, so it's undocumented-by-example rather than unsupported.

## Context
This follows directly from the prior question in this session ("How to reference a hypernode in graph 'alpha' as a member in a hyperedge in graph 'bravo'?"), which established that cross-graph *member references* (`EdgeMember.node_id`) aren't supported, but that mesh dot-notation and logical-graph composition exist as query-time (`from:` clause) mechanisms. This question asked for the precise syntax of those query-time mechanisms. Investigated via the HQL/SHQL engine resolution code and cross-checked every syntax form against verbatim example query strings already present in `README.md` and `docs/concepts.md`, rather than inferring syntax from code structure alone.
