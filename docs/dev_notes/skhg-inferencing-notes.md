# Semantic Knowledge Hypergraph Inferencing

> **SUPERSEDED.** This note describes an early design sketch — axiom hyperedges asserted with a placeholder `relation: is` and the axiom name as a member (e.g. `members: [rel:contains, owl:transitive]`) — that predates the actual implementation. The mechanism that was actually built and shipped (`hgai/core/inference.py`, wired into SHQL behind `infer: true`) instead asserts the axiom hyperedge's own `relation` field as the axiom name itself (e.g. `relation: owl:transitive`), with the target relation(s) as members — see the [README's Inferencing section](../../README.md#inferencing) for the current, correct mechanics and worked examples. Kept here for historical reference only; do not follow the examples below.

## Inference Relations

- `skos:broader` : broader concept
- `skos:narrower` : narrower concept
- `owl:inverse-of` : inverse relationship
- `owl:transitive` : transitive chain
- `owl:symmetric` : symmetric relations a -> b, b -> a

## Hyperedge Flavors
- `hub` : first member direct relationship with subsequent members
- `symmetric` : all members related same

(`transitive`/`inverse-transitive` flavors were considered and dropped: a
directed chain is several independent binary facts, not one N-ary fact, so
it's modeled as separate two-member `hub` edges. Cross-edge transitive
reachability is handled by the `owl:transitive` inference relation above,
applied across those edges — not by a per-edge flavor.)

## How to Declare Semantic Relations?

- Hyperedge
  - relation: valid inference relation (e.g. `skos:browser`, `owl:transitive`)
  - first member; subject; relation hypernode id
  - second member; predicate; target hypernode id
  - relations are hypernodes/entities

### SKOS Broader / Narrower Relations

hyperedge:
```yaml
  # ...
  members:
  - node_id: rel:family.sibling
    seq: 0
  - node_id: rel:family.related 
    seq: 1
  relation: skos:broader
  flavor: hub
  # ...
```

### Transitive Relations

hyperedge:
```yaml
  # ...
  members:
  - node_id: rel:contains
    seq: 0
  - node_id: owl:transitive 
    seq: 1
  relation: is
  flavor: hub
```

hyperedge:
```yaml
  # ...
  members:
  - node_id: rel:contained-by
    seq: 0
  - node_id: owl:transitive 
    seq: 1
  relation: is
  flavor: hub
```

### Inverse-Of Relations

hyperedge:
```yaml
  # ...
  members:
  - node_id: rel:contains
    seq: 0
  - node_id: rel:contained-by 
    seq: 1
  relation: owl:inverse-of
  flavor: hub
```

hyperedge:
```yaml
  # ...
  members:
  - node_id: rel:parent
    seq: 0
  - node_id: rel:child 
    seq: 1
  relation: owl:inverse-of
  flavor: hub
```

### Symmetric Relations

hyperedge:
```yaml
  # ...
  members:
  - node_id: rel:family.sibling
    seq: 0
  - node_id: owl:symmetric 
    seq: 1
  relation: is
  flavor: hub
```
