---
id: help-what-is-hgai
label: What is HypergraphAI?
name: what-is-hypergraphai
description: The idea behind HypergraphAI, what makes it different, and where it fits.
tags: ["//Getting Started", overview, hypergraph, introduction]
status: active
---

# What is HypergraphAI?

HypergraphAI stores and queries knowledge as **hypergraphs**. In an ordinary graph an edge joins exactly two nodes. In a hypergraph a single **hyperedge** can join *n* nodes at once — which is how people and AI agents naturally describe the world: "Moe, Larry and Curly were members of the Three Stooges in 1940" is *one* fact, not three unrelated pairs.

## What makes it different

- **Hyperedges are first-class entities.** They carry their own document attributes, tags and status, and can even take part in other edges.
- **Semantic relationships.** Relation semantics (transitive, symmetric, inverse-of, broader/narrower — SKOS/OWL-style) are declared as ordinary data, then applied by the [inference engine](help:help-inferencing) at query time.
- **Temporal awareness.** Nodes and edges carry `valid_from` / `valid_to`, so [point-in-time queries](help:help-point-in-time) can answer "what was true on this date?".
- **Document-flexible.** Every node and edge has a free-form JSON `attributes` document — no schema migration to add a property.
- **AI-native.** All operations are exposed as [MCP tools](help:help-mcp-server), and the Web UI has a built-in [AI Chat agent](help:help-ai-chat).
- **Modular.** Storage, security, SHQL, meshes, MCP and the agent chat are pluggable [modules](help:help-modules).
- **RBAC.** [Role-based access control](help:help-accounts-roles) covers every operation, with [spaces](help:help-spaces) for multi-tenant isolation.

## How it's put together

![Component layers](help-media:hgai-component-layers.svg)

The Web UI, the [hgsh shell](help:help-shell), and external AI clients all sit on top of two front doors — the [REST API](help:help-rest-api) (FastAPI) and the [MCP server](help:help-mcp-server) (FastMCP). Both call the same core engine (query, inference, auth, cache, temporal), which persists to MongoDB through a pluggable storage layer.

## What you'll typically do with it

1. Model a domain as [hypernodes](help:help-hypernodes) and [hyperedges](help:help-hyperedges) in a [hypergraph](help:help-hypergraphs).
2. Explore it in the [Visualize](help:help-visualize) screen or the node/edge tables.
3. Ask questions with [SHQL](help:help-shql-overview), or let an AI agent do so through [MCP](help:help-mcp-server) or the [AI Chat](help:help-ai-chat).
4. Federate several servers into a [mesh](help:help-meshes) and query across them.

Ready to try it? Continue to the [Quick Start](help:help-quick-start).
