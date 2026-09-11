# Mutation Log

## Created
- **tests/test_inference.py** — 8 unit tests for `atomic_pairs()`: hub fan-out from the seq-0 member, decomposition ordered by `seq` not list position, binary hub case, empty-members case, symmetric full directed clique (3 and 2 members), acceptance of member-like objects (not just dicts, e.g. `EdgeMember` instances), and rejection of any flavor other than `hub`/`symmetric`.

## Modified
- **hgai/core/inference.py** — Added the three Step 1/2 shared primitives specified in the inferencing plan:
  - `atomic_pairs(members, flavor)` — pure function decomposing a hyperedge's members into directed binary `(subject, object)` facts. `hub`: seq-0 member is the hub, paired with every other member. `symmetric`: full directed clique (every ordered pair). Raises `ValueError` for any other flavor value.
  - `get_axiom_edges(relation_id, axiom, graph_ids, pit=None)` — async lookup for axiom hyperedges (ordinary hyperedges whose `relation` is a control-vocabulary string like `"owl:transitive"`/`"skos:narrowerTransitive"` and whose members include `relation_id`), built on `find_for_transitive`.
  - `walk_closure(start_id, relation, graph_ids, direction="forward", max_depth=10, pit=None)` — generic cycle-safe BFS over hyperedges of one relation, decomposing each via `atomic_pairs` for adjacency; shared by fact-graph transitive-reachability walks and axiom-graph superproperty-projection walks. Returns `{reached_node_id: via_hyperedge_id}`.
  - Updated the module docstring to describe the "relations are data, never hardcoded" design and note `infer_inverse_edges`/`check_transitive_relation` are being migrated onto these primitives, not yet wired into any query path.
- **hgai_module_storage/filters.py** — Added `pit: Optional[datetime] = None` to `TransitiveSearchFilter`, matching the pattern already used by every other PIT-aware filter dataclass in this module.
- **hgai_module_storage/backend.py** — Updated `HyperedgeStore.find_for_transitive`'s abstract docstring to describe the widened return shape (full documents, not just `members`) and PIT semantics.
- **hgai_module_storage_mongodb/stores/hyperedges.py** — `find_for_transitive()`: (1) widened the Mongo query projection from `{"members": 1}` to full documents, so callers can read `id`, `relation`, `flavor`, etc.; (2) added `_pit_clause` filtering when `filters.pit` is set (same helper already used by `list()`); (3) added the missing `doc.pop("_id", None)` (previously the returned dicts carried a non-JSON-serializable raw Mongo `_id`, harmless only because the sole existing caller ignored every field but `members`).
