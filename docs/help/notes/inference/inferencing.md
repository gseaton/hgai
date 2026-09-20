---
id: help-inferencing
label: Inferencing
name: inferencing
description: How HypergraphAI derives implicit facts — inverse-of, symmetric, superproperty and transitive axioms, computed live behind infer:true.
tags: ["//Inferencing", inference, axiom, transitive, symmetric, inverse-of, skos, owl]
status: active
---

# Inferencing

The inference engine derives implicit knowledge from the relationships you stored — **computed live at query time; nothing inferred is persisted** (unless you choose [Project Inference](help:help-project-inference)).

## Rules are data, not code

Relation semantics are never hardcoded. They are declared as ordinary **axiom hyperedges** between `RelationType` hypernodes, using a small control vocabulary:

`owl:transitive`, `owl:symmetric`, `owl:inverse-of`, `skos:broaderTransitive`, `skos:narrowerTransitive`.

Declaring a new inference rule is therefore a **data change** (create an axiom hyperedge), not a code change.

## Turning it on

Inferencing is opt-in per query: add `infer: true` to an [SHQL](help:help-shql-overview) query. It has no effect unless the query matches a `relation:` that actually carries an axiom in the queried graph. In the [Visualize](help:help-visualize) screen use **Show inferred edges**.

## Axiom expansion

| Axiom | Effect |
|---|---|
| `owl:inverse-of [R, R']` | For a hub-flavor edge, each (hub, spoke) fact of `R` also implies `R'(spoke, hub)`. E.g. `rel:member` ↔ `rel:member-of` (declared in the `hello-world` seed). |
| `owl:symmetric` | Every member of a symmetric-flavor edge is equivalent to every other: A related-to B implies B related-to A. |
| `skos:broaderTransitive` / `narrowerTransitive` | *Superproperty projection*: if relation `father` is narrower than `parent`, which is narrower than `ancestor`, a `father` fact is copied to `parent` and `ancestor`, through every level. |
| `owl:transitive` | Whole-relation reachability: given `parent` facts A→B→C and an `owl:transitive` axiom on `parent`, it synthesizes A→C. |

The expansion repeats to a fixed point (bounded by `max_iterations`) and de-duplicates by atomic (relation, subject, object) fact, so the same fact reached two ways — or through a cyclic axiom graph — is returned once.

## Recognizing inferred edges

Inferred edges carry `_inferred: true`, `_source_edge` (the literal edge it came from; `null` for a transitive result) and `_axiom` (the axiom hyperedge that licensed it). A transitive result also has `_transitive: true` and `_transitive_path` (the chain of literal edge ids). Because inferred edges are spliced in *before* pattern matching, they behave like literal ones — they can bind variables and anchor later hops.

## Transitive reachability question

Separately, you can ask one targeted question — *is A transitively connected to B by relation R?* (or *what is everything reachable from A?*, or *what's the path?*) — without composing a query: `POST /api/v1/graphs/{graph}/infer/transitive`, or the `hgai_infer_check_transitive` MCP tool. It is a cycle-safe breadth-first walk (`max_depth` 10 by default) that only fires for relations with an `owl:transitive` axiom.

Edge decomposition rules are in [Edge flavors](help:help-edge-flavors). To persist derived facts, see [Project Inference](help:help-project-inference).

## Planned

Rule-based inferencing (user-defined `InferenceRule` nodes), cross-graph inferencing, a materialized inference cache, and OWL-lite property chains.
