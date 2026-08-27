# Response Summary

## Question / Intent
The user wanted to know the mechanism/identifier format for making a hyperedge that lives in one hypergraph ('bravo') reference, as one of its members, a hypernode that lives in a different hypergraph ('alpha').

## Answer / Recommendation
Cross-graph member referencing is not supported today. There is no code path, identifier format, or field that lets an `EdgeMember` cross a `hypergraph_id` boundary:

- `EdgeMember` (`hgai/models/hyperedge.py:25-32`) has only `node_id: str` and `seq: int` — no `graph_id` field and no graph-qualified id string format (e.g. `"alpha:person:moe"`) is parsed anywhere in the codebase.
- A hyperedge's `hyperkey` and all of its members are implicitly scoped to the single `hypergraph_id` of the enclosing hyperedge (`hgai/core/engine.py:246-267`, `_hypergraph_ref` helper at `hgai/core/engine.py:49-58`).
- The `POST /graphs/{graph_id}/edges` API takes `graph_id` as one path parameter scoping the entire create request; the request body has no per-member graph override (`hgai/api/routers/hyperedges.py:65`).
- Notably, member existence isn't validated at all today — `create_hyperedge` stores `node_id` as an opaque string with no lookup against any store (same-graph or cross-graph), so there's also no validation layer that would need to be taught about cross-graph refs.

If this capability is wanted, the natural extension point (not implemented, just identified) would be: add an optional `graph_id` (or a qualified-id string reusing the existing `space_id/graph_id` convention) to `EdgeMember`, and add real member-resolution logic in `create_hyperedge` that honors a per-member override instead of always defaulting to the enclosing hyperedge's `hypergraph_id`.

## Key Points
- **Logical graph composition** (`Hypergraph.composition: List[str]`, `hgai/models/hypergraph.py:41-44`) is the closest-sounding existing feature but doesn't solve this: it lets a virtual graph union several graphs for *querying* (nodes from `alpha` and `bravo` can appear together in one query result), but any given hyperedge still physically lives in exactly one graph — it does not let a single edge's members span graphs.
- **Mesh dot-notation** (`mesh_id.server_id.graph_id`, implemented in `hgai_module_mesh/engine.py:249-286`) is a graph-qualified identifier format that does exist in the codebase, but it is exclusively for the HQL `from:` clause when federating read queries across separate *server instances* (see `tests/test_mesh.py::test_federated_hql_merges_results`, which merges query result items over HTTP) — it is unrelated to `EdgeMember.node_id` and cannot be used as a member reference.
- `Hypergraph.id`, `MeshServer.server_id`, and `Mesh.id` all explicitly forbid `.` in their values specifically because `.` is reserved for mesh dot-notation (`hgai/models/hypergraph.py:32-36`, `hgai_module_mesh/models.py:16-20,33-37`) — further confirming that identifier format's exclusive association with mesh federation, not member references.

## Context
Investigated via a full read of the hypernode/hyperedge model definitions, the hyperedge creation path in `hgai/core/engine.py`, the MongoDB storage layer's query-scoping (`hgai_module_storage_mongodb/stores/hyperedges.py`), the API router (`hgai/api/routers/hyperedges.py`), architecture docs (`docs/architecture/hypergraph_ai_design_notes.md`), and the mesh module (`hgai_module_mesh/models.py`, `hgai_module_mesh/engine.py`) to distinguish mesh's server-federation concept from a same-server cross-graph reference, which are easy to conflate but are unrelated mechanisms.
