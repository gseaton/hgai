# Response Summary

## Question / Intent
Following on from the prior question about cross-graph `EdgeMember` references (not supported), the user asked for the actual query-time syntax: how HQL and SHQL's `from:` clause lets a query reach hypernodes/hyperedges in a different graph, a different space, or a remote graph on another mesh server.

## Answer / Recommendation
HQL and SHQL share byte-for-byte identical `from:` resolution logic — confirmed by reading both engines (`hgai_module_hql/engine.py:231-278` vs the equivalent block in `hgai_module_shql/engine.py:901-953`, which use the literal same `r.count(".") in (2, 3)` partitioning). There is no syntax difference between the two languages for any of the reference forms below; they only differ in the query body underneath `from:` (HQL: `match`/`where`/`return`, Mongo-filter style; SHQL: `where`/`select` with `?var` SPARQL-style pattern matching).

Four reference forms, all usable as a single `from:` string or inside a YAML list under `from:` (list entries can freely mix forms):

1. **Same-server, different graph (unowned)** — plain graph id: `from: hello-world`
2. **Space-scoped graph (same server)** — slash separator: `from: alpha/alpha-hg` (`space_id/graph_id`)
3. **Mesh remote graph, dot-notation** — `mesh.server.graph` (unowned, 2 dots) or `mesh.server.space.graph` (space-scoped, 3 dots), with `*` wildcards allowed for the server or graph component: e.g. `from: my-mesh.remote-server.alpha.alpha-hg`
4. **Bare mesh id** — `from: alpha-bravo-mesh` federates the query across every server in that mesh concurrently (not a specific graph)

A YAML list under `from:` (e.g. `from: [hello-world, alpha/alpha-hg]`) queries multiple targets in one call; the engine partitions the list into dot-notation mesh refs vs plain local/space refs before resolving each.

## Key Points
- Dots are reserved exclusively for mesh routing — `Hypergraph.id`, `MeshServer.server_id`, and `Mesh.id` all forbid `.` in their values specifically so that splitting a `from:` ref on `.` is unambiguous (`hgai/models/hypergraph.py:32-36`, `hgai_module_mesh/models.py:16-20,33-37`). This is why dot-count alone (2 vs 3) is enough to distinguish the two dot-notation forms and separate them from space-scoped (`/`) or plain refs.
- The 3-part vs 4-part dot forms also support wildcards: `mesh.*.graph` (unowned graph across all servers), `mesh.*.space.graph`, and `mesh.server.*` (all unowned graphs on one server) — parsed in `hgai_module_mesh/engine.py:248-265` (`_parse_dot_ref`).
- Mesh dot-refs and mesh-wide bare-id refs are resolved concurrently via `asyncio.gather`, so total latency is bounded by the slowest server, not the sum — documented in README.md:1539,1581 and implemented in `hgai_module_mesh/engine.py`'s `resolve_dot_refs`/`execute_dot_refs`.
- Logical graph composition (`Hypergraph.composition`) is transparently expanded inside `_resolve_graph_ids`/its SHQL equivalent when a `from:` ref points at a logical graph — each constituent graph's ref is resolved and unioned automatically, so composed graphs don't need any special `from:` syntax of their own.

## Context
Read `hgai_module_hql/engine.py` (particularly `_resolve_graph_ids` at line 231 and the dot/plain ref partitioning in `execute_hql` around line 306-353) and the equivalent SHQL block in `hgai_module_shql/engine.py:878-953`, plus `hgai_module_mesh/engine.py:248-369` (`_parse_dot_ref`, `resolve_dot_refs`, `execute_dot_refs`) for the mesh routing implementation. Cross-checked every syntax claim against verbatim, working example queries already present in `README.md` (space-scoped: lines 367-463; mesh dot-notation table and examples: lines 1583-1617; mesh SHQL examples: lines 1537-1577) rather than describing the grammar from code alone — all forms cited here have at least one real example in the docs, not a fabricated one.
