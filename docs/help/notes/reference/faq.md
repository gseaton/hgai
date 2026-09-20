---
id: help-faq
label: Frequently asked questions
name: faq
description: Quick answers to the questions new users ask most, with links to the full topics.
tags: ["//Reference", faq, troubleshooting, questions]
status: active
---

# Frequently asked questions

## Concepts

**What's the difference between a hypergraph and an ordinary graph?**
In an ordinary graph an edge joins two nodes. A [hyperedge](help:help-hyperedges) joins any number, so a fact like "these five people were members of this group in this era" is one edge. See [What is HypergraphAI?](help:help-what-is-hgai).

**Do I need to define a schema first?**
No. Nodes and edges carry a free-form `attributes` JSON document; only `id`, `label` and `type`/`relation` are structured ([Hypernodes](help:help-hypernodes)).

**What does `hub` versus `symmetric` mean?**
See [Edge flavors](help:help-edge-flavors): in a hub edge the first member is related to each of the others; in a symmetric edge everyone is related to everyone.

**Can I see what was true on a past date?**
Yes — set `valid_from`/`valid_to` and query with `at:` ([Point-in-time](help:help-point-in-time)).

**How do I make the system infer that "has-member" implies "member-of"?**
Create an `owl:inverse-of` axiom hyperedge between the two relation types and query with `infer: true` ([Inferencing](help:help-inferencing)).

## Using it

**How do I load sample data?** Run `python scripts/seed_data.py` (or the `docker-compose exec` form) — the `hello-world` graph appears ([Quick Start](help:help-quick-start)).

**How do I query?** Open **Query (SHQL)** ([Query screen](help:help-query-screen)) and start with the [SHQL overview](help:help-shql-overview) and [worked examples](help:help-shql-examples).

**How do I reuse a query with different values?** Save it as a [parameterized query](help:help-parameterized-queries) with `/$name:type:default$/` placeholders.

**Why does my query return nothing?** Check that `from:` names the right graph (`space/graph` for space graphs); that `type:`/`relation:` spelling matches the data; that a node `status` isn't `draft`/`archived` (patterns default to `active`); that `at:` isn't excluding everything; and try **Validate**. Turn the **Cache** toggle off if data just changed.

**Why are my results cut off?** Results default to `limit: 500`. Add `limit:`/`offset:`.

**How do I ask the AI about my data?** Open the [AI Chat](help:help-ai-chat) panel (an admin must enable a vendor, key and model first).

**Where do I write documents?** In [Notes](help:help-notes); tag with `//Folder/Name` to file them in a folder.

## Access and integration

**How do I connect Claude Desktop or another AI tool?** Use the [MCP server](help:help-mcp-server) with an [API key or token](help:help-authentication).

**I get "Unauthorized" / 401.** Your token expired (default 8 hours) or is missing; log in again ([Authentication](help:help-authentication)).

**I can log in but can't see a hypergraph.** Check your account's `permissions.graphs`, or, for a space graph, whether you are a member of that space ([Spaces](help:help-spaces), [Accounts and roles](help:help-accounts-roles)).

**How do I query several servers?** Register them in a [mesh](help:help-meshes) and use dot-notation `from:` references.

## Operations

**What's the default login?** `admin` / `pwd357` — change it immediately ([Accounts and roles](help:help-accounts-roles)).

**Which port?** 8357 locally, 8000 under Docker Compose ([Running locally](help:help-running-locally), [Docker](help:help-docker)).

**How do I back up?** Use `mongodump` ([Backup](help:help-backup)).

**Can I add my own help pages?** Yes — files or `system:help` notes ([Adding your own help topics](help:help-authoring-help)).

Still stuck? Browse the [Glossary](help:help-glossary) or return [Home](help:help-home).
