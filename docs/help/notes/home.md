---
id: help-home
label: Welcome to HypergraphAI
name: home
description: Start here — what HypergraphAI is, and quick links to the topics that answer most questions.
tags: ["//Getting Started", welcome, overview]
status: active
---

# Welcome to HypergraphAI

**HypergraphAI (hgai)** is a hybrid semantic hypergraph document platform. It stores knowledge as a **hypergraph** — a network in which one relationship (a *hyperedge*) can connect **any number** of things at once — and keeps every entity and relationship as a flexible JSON document, so you get the expressiveness of a knowledge graph with the convenience of a document database.

It is built for people *and* AI agents: everything you can do in the Web UI is also available through a REST API, an interactive shell, and an MCP (Model Context Protocol) server that AI tools such as Claude can call directly.

![The layers of HypergraphAI](help-media:hgai-component-layers.svg)

## In one minute

| Building block | What it is | Example |
|---|---|---|
| **Hypernode** | An entity, with an id, label, type, tags and a free-form `attributes` document | `moe-howard` (a `Person`) |
| **Hyperedge** | A relationship connecting *n* hypernodes — a first-class object with its own attributes | `has-member` linking `three-stooges`, `moe-howard`, `larry-fine`, `curly-howard` |
| **Hypergraph** | A named container of hypernodes and hyperedges | `hello-world` |
| **SHQL** | The pattern-matching query language (YAML, SPARQL-inspired) | "who was in the group in 1940?" |

Because every hyperedge is timestamped and versioned, you can also ask questions **as of a point in time**, and derive new facts automatically with **inferencing** (inverse, symmetric, and transitive relations).

## Common questions — jump straight in

**Getting started**
- New here? Read [What is HypergraphAI?](help:help-what-is-hgai) and then the [Quick Start](help:help-quick-start).
- Can't find something? Try the [FAQ](help:help-faq) or the [Glossary](help:help-glossary).

**Understand the model**
- [Hypernodes](help:help-hypernodes), [Hyperedges](help:help-hyperedges) and [Hypergraphs](help:help-hypergraphs)
- [Edge flavors](help:help-edge-flavors) (hub vs. symmetric) and [Point-in-time queries](help:help-point-in-time)
- [Spaces](help:help-spaces) — multi-tenant namespaces

**Use the Web UI**
- [Web UI tour](help:help-web-ui) — every screen in one page
- [Notes](help:help-notes), [Media](help:help-media), [Visualize](help:help-visualize)
- [Run an SHQL query](help:help-query-screen) and save reusable [Parameterized Queries](help:help-parameterized-queries)
- [Ask the AI Chat agent](help:help-ai-chat) about your data, or about HypergraphAI itself

**Query your knowledge**
- [SHQL overview](help:help-shql-overview) → [patterns](help:help-shql-patterns) → [filters](help:help-shql-filters) → [worked examples](help:help-shql-examples)
- [Inferencing](help:help-inferencing) — derive facts you never stored

**Connect other tools**
- [REST API](help:help-rest-api) and [authentication](help:help-authentication)
- [MCP server](help:help-mcp-server) — let AI agents read and write your hypergraphs
- [The hgsh shell](help:help-shell)

**Run and administer**
- [Configuration](help:help-configuration), [running locally](help:help-running-locally), [Docker](help:help-docker)
- [Accounts and roles](help:help-accounts-roles), [Meshes](help:help-meshes), [Backup](help:help-backup)

## Finding your way around this Help tab

- The **Topics** tree on the left groups topics into folders. Click a topic to open it.
- Use the **search** box (every word must match) or **filter by tag** to list matching topics; click any tag badge to see everything with that tag. **All Topics** lists everything.
- **Back** returns to the previous topic and **Home** brings you back here.
- You can add your own help pages — see [Adding your own help topics](help:help-authoring-help).
