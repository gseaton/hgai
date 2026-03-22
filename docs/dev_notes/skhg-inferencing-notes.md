# Semantic Knowledge Hypergraph Inferencing

## Inference Relations

- `skos:broader` : broader concept
- `skos:narrower` : narrower concept
- `owl:inverse-of` : inverse relationship
- `owl:transitive` : transitive chain
- `owl:symmetric` : symmetric relations a -> b, b -> a

## Hyperedge Flavors
- `hub` : first member direct relationship with subsequent members
- `symmetric` : all members related same
- `transitive` : first member -> second member, second member -> third member, n-1 member -> n member
- `inverse-transitve` : n member -> n - 1 member; ... ; third member -> second member; second member -> first member

## How to Declare Symmetric Relations?

- Hyperedge
  - relation: valid inference relation (e.g. `skos:browser`, `owl:transitive`)
  - first member; subject; relation hypernode id
  - second member; predicate; 