---
id: help-edge-flavors
label: Edge flavors
name: edge-flavors
description: How a hyperedge's member list decomposes into facts — hub versus symmetric flavors.
tags: ["//Concepts", flavor, hub, symmetric, hyperedge]
status: active
---

# Edge flavors

A hyperedge's `flavor` describes how its **member list** breaks down into individual (subject, object) facts. It is *unrelated* to transitivity, which is a property of a *relation*, declared with an `owl:transitive` axiom (see [Inferencing](help:help-inferencing)).

| Flavor | Semantics |
|---|---|
| `hub` | The first member (lowest `seq`) is the **hub**; every other member is an independent (hub, spoke) fact. "adam is father of cain, abel and seth" is **three** separate facts, not one N-ary fact. |
| `symmetric` | Every member is mutually equivalent to every other. `sibling(moe, larry, curly)` implies all six directed pairs. |

The API also recognizes `direct`, `transitive` and `inverse-transitive` flavor values.

## Why it matters

- The [inference engine](help:help-inferencing) uses flavor when it applies `owl:inverse-of` (hub edges) and `owl:symmetric` axioms.
- In [SHQL](help:help-shql-patterns) you can require a specific flavor (`flavor: hub`) and a specific position (`seq: 0`) — e.g. "the hub of the edge is this group".

Related: [Hyperedges](help:help-hyperedges).
