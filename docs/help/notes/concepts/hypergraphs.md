---
id: help-hypergraphs
label: Hypergraphs
name: hypergraphs
description: A hypergraph is a named container of hypernodes and hyperedges — instantiated or logical, local or federated.
tags: ["//Concepts", hypergraph, container, logical, instantiated]
status: active
---

# Hypergraphs

A **hypergraph** is a named container for [hypernodes](help:help-hypernodes) and [hyperedges](help:help-hyperedges). Every node and edge belongs to exactly one hypergraph, and the graph's `id` is part of their identity (so two graphs can each have a node called `alice`).

## Types

- **Instantiated** — a physical collection of nodes and edges in MongoDB. This is the normal kind.
- **Logical** — a virtual composition of one or more other hypergraphs (local or remote). Querying a logical graph expands to its component graphs.

## Fields

`id` (slug), `label`, `description`, `graph_type` (`instantiated` or `logical`), `tags`, `status` (`active`, `draft`, `archived`).

## Ownership: unowned graphs and spaces

A hypergraph is either **unowned** (referenced by its bare id, e.g. `my-graph`) or owned by a [space](help:help-spaces) (referenced `space_id/graph_id`, e.g. `alpha/alpha-hg`).

## Operations

- **Web UI** — **Hypergraphs** screen: create, edit, delete, and view a graph's statistics.
- **REST** — `/api/v1/graphs` (plus `/stats`, `/export`, `/import`) ([REST API](help:help-rest-api)).
- **Move between servers** — export a graph to an `hgai-hypergraph-…export.yml` file and import it elsewhere ([Exporting and importing hypergraphs](help:help-export-import)).
- **MCP** — `hgai_hypergraph_list`, `_get`, `_stats`, `_create` ([MCP tools](help:help-mcp-tools)).
- **Across servers** — register servers in a [mesh](help:help-meshes) and query graphs on any of them.

Deleting or changing a hypergraph flushes the whole [query cache](help:help-indexes-performance); ordinary node/edge writes only evict entries that touched that graph.
