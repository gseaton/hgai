# Response Summary

## Question / Intent
Design a YAML-based format (JSON-equivalent) for representing HypergraphAI hypernodes and hyperedges, drawing on RDF Turtle for terseness, where hyperedges are a special type of hypernode and node properties go in `attributes:` not as edges.

## Answer / Recommendation

**Format name:** hgai v1.0

**Core structure:**
```yaml
hgai: "1.0"
prefixes: {}   # optional
nodes: []      # flat list of all hypernodes and Rel nodes
```

**Key design decision — `type: Rel` as the hyperedge discriminator:**
Everything lives in a single `nodes:` list. A node with `type: Rel` is simultaneously a hypernode AND a hyperedge. It carries all standard node fields (id, label, tags, status, valid_from, valid_to, attributes) PLUS edge-specific fields (relation, flavor, members).

**Regular hypernode fields:** id (required), label (required), type (default: Entity), description, tags, status (default: active), valid_from, valid_to, attributes (arbitrary key-values).

**Rel node additional fields:** relation (required), flavor (default: hub; options: hub/symmetric/direct/transitive/inverse-transitive), members (required; compact list of node IDs with implicit seq from list position, OR verbose `{id, seq}` form for explicit ordering). `id` is optional on Rel nodes — omitting it triggers auto-generation matching API behavior.

**Compact member syntax (primary form):**
```yaml
members:
  - g:three-stooges   # seq 0 — conventionally the hub
  - p:moe-howard      # seq 1
  - p:larry-fine      # seq 2
```

**Verbose member syntax (machine round-trip):**
```yaml
members:
  - {id: g:three-stooges, seq: 0}
  - {id: p:moe-howard, seq: 1}
```

**Prefix expansion:** `prefixes: { p: "person:" }` lets you write `p:moe-howard` in the file, which expands to `person:moe-howard` for the API. Plain strings without prefixes always work.

**Date shorthand:** `"YYYY-MM-DD"` accepted; expanded to `"YYYY-MM-DDT00:00:00Z"` at import time.

**JSON equivalence:** Trivial — YAML is a superset of JSON; the same structure works in JSON with no schema changes.

## Key Points
- Single flat `nodes:` list — no separate `edges:` block. One pass, one list.
- `type: Rel` is the only reserved type. Other types (Person, Group, Organization, etc.) are unreserved plain strings.
- Omitting `status`, `type`, `flavor`, `id` (on Rel), and `prefixes` reduces boilerplate for human authoring.
- Compact member list (list position = seq) covers the common case; verbose form exists for tooling.
- The `g:three-stooges` convention (hub node at seq 0 in a hub-flavor edge) is a convention, not enforced by the format.
- `attributes:` block holds ALL node properties (last_name, dob, etc.) — never as child nodes or edges.

## Context
Format designed against the HypergraphAI API schema (hypernodes: id/label/type/description/tags/status/valid_from/valid_to/attributes; hyperedges: id/relation/flavor/label/members[{node_id,seq}]/status/tags/valid_from/valid_to/attributes). The `type: Rel` name aligns with the existing `RelationType` node type suggestion in the UI and the existing `rel:` prefix convention seen in HQL example queries.
