Please generate a plan to add `organization` as the parent entity of `space`:

- `space` identifiers are unique in their parent `organization` and do NOT need to be unique across the hgai server
- all child elements of `space` (i.e. `hypergraph`, `hyperedges`, `hypernodes`, `meshes`, `accounts`, etc) will also contain an `_org_id` that will be associated with its parent `organization`
- 