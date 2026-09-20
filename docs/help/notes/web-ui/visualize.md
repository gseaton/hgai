---
id: help-visualize
label: Visualize
name: visualize
description: The interactive 3D hypergraph view — selecting graphs, filtering, point-in-time, and showing inferred edges.
tags: ["//Using the Web UI", visualize, graph, 3d, inference]
status: active
---

# Visualize

**Visualize** renders one or more hypergraphs as an interactive 3D scene: hypernodes as objects and each [hyperedge](help:help-hyperedges) as a hub connecting all its members — which is how an *n*-ary relationship stays legible.

## Controls

| Control | What it does |
|---|---|
| **Hypergraph(s)** | Which graphs to draw (one or several) |
| **Status** | Show active (default), all, archived or draft items |
| **Search** | Filter by label |
| **At (point-in-time)** | Render only hyperedges valid at that instant. Hypernodes always render ([Point-in-time](help:help-point-in-time)) |
| **Labels** | Toggle text labels |
| **Media** | Show attached default media on nodes |
| **Auto-rotate** | Slowly spin the scene |
| **Hide orphan nodes** | Hide nodes that are not a member of any hyperedge |
| **Show inferred edges** | Also draw facts derived from inverse-of / symmetric / superproperty / transitive axioms — computed live, never persisted ([Inferencing](help:help-inferencing)) |

Selecting an item shows its details in a collapsible side panel, and you can focus on one node's neighborhood (and clear the focus again).

To make derived facts permanent, use [Project Inference](help:help-project-inference).
