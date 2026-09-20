---
id: help-glossary
label: Glossary
name: glossary
description: Definitions of HypergraphAI terms — hypernode, hyperedge, hyperkey, flavor, SHQL, axiom, mesh, space, and more.
tags: ["//Reference", glossary, terms, definitions]
status: active
---

# Glossary

| Term | Meaning |
|---|---|
| **Hypergraph** | A named container of hypernodes and hyperedges ([more](help:help-hypergraphs)) |
| **Hypernode** | An entity with id, label, type, attributes and tags ([more](help:help-hypernodes)) |
| **Hyperedge** | A first-class relationship connecting *n* hypernodes ([more](help:help-hyperedges)) |
| **Relation** | The type of a hyperedge, e.g. `has-member` |
| **Member** | One participant of a hyperedge: `node_id`, `seq`, optional role |
| **`seq`** | A member's position in a hyperedge; `seq: 0` is the first member |
| **Flavor** | How a hyperedge's members decompose into facts — `hub`, `symmetric`, … ([more](help:help-edge-flavors)) |
| **Hyperkey** | SHA-256 hash of an edge's normalized structure; prevents duplicate facts |
| **Instantiated / logical graph** | Physical graph vs. a virtual composition of other graphs |
| **PIT (point-in-time)** | Querying the state valid at an instant with `at:` ([more](help:help-point-in-time)) |
| **SHQL** | Semantic Hypergraph Query Language ("shekel") ([more](help:help-shql-overview)) |
| **Binding / variable** | A `?name` bound to a matched node or edge; sharing one across patterns is a join |
| **Axiom** | A hyperedge declaring a relation's semantics (`owl:transitive`, `owl:symmetric`, `owl:inverse-of`, `skos:broaderTransitive`) ([more](help:help-inferencing)) |
| **Inferred edge** | A synthesized edge tagged `_inferred: true`; computed live |
| **Projection** | Persisting inferred edges into a graph ([more](help:help-project-inference)) |
| **Space** | A multi-tenant namespace for graphs, with member roles ([more](help:help-spaces)) |
| **Mesh** | A registry of servers queried together ([more](help:help-meshes)) |
| **Dot-notation** | `mesh.server.space.graph` references to remote graphs |
| **MCP** | Model Context Protocol — how AI agents call hgai tools ([more](help:help-mcp-server)) |
| **Note** | A Markdown document with tags, sharing and media ([more](help:help-notes)) |
| **Virtual folder** | A `//Folder/Sub` tag shown as a folder in the Notes and Help trees |
| **Parameterized query** | A saved SHQL template with `/$name$/` placeholders ([more](help:help-parameterized-queries)) |
| **Media** | An uploaded file attachable to nodes, edges and notes ([more](help:help-media)) |
| **Help topic** | A markdown file (or `system:help` note) shown in this Help tab ([more](help:help-authoring-help)) |
| **Module** | A pluggable `hgai_module_<name>` subsystem ([more](help:help-modules)) |
| **hgsh** | The interactive shell ([more](help:help-shell)) |
