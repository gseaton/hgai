---
id: help-quick-start
label: Quick Start
name: quick-start
description: Get a HypergraphAI server running, log in, and load the hello-world sample data.
tags: ["//Getting Started", install, docker, setup]
status: active
---

# Quick Start

## Prerequisites

- Docker and Docker Compose (recommended), **or** Python 3.11+ with a MongoDB 7+ instance for local development.

## Option A — Docker Compose

```bash
git clone <repo-url>
cd hgai
cp .env.example .env        # edit as needed
docker-compose up -d
docker-compose exec hgai python scripts/seed_data.py   # optional: load hello-world
```

This starts MongoDB and the HypergraphAI server. With Docker Compose the server listens on **port 8000**:

- Web UI: `http://localhost:8000/ui/`
- API docs: `http://localhost:8000/api/docs`
- MCP server: `http://localhost:8000/mcp/`

## Option B — Local development

```bash
pip install -r requirements.txt
cp .env.example .env
./hgai.sh                       # default port 8357
python scripts/seed_data.py     # optional sample data
```

The Web UI is then at `http://localhost:8357/ui/`. See [Running locally](help:help-running-locally) for ports, multiple parallel servers, and options.

## Log in

The default administrator is **admin** with password **pwd357**. **Change this password immediately** (Accounts screen) — see [Accounts and roles](help:help-accounts-roles).

## The hello-world data

`scripts/seed_data.py` loads a small Three Stooges hypergraph called `hello-world`: `Person` nodes such as `moe-howard`, and `has-member` hyperedges recording who belonged to the group in which era. Most documentation examples use it.

## Try something

1. Open **Hypergraphs** and select `hello-world`, then browse **Hypernodes** and **Hyperedges**.
2. Open **Visualize**, choose the graph, and explore it visually ([Visualize](help:help-visualize)).
3. Open **Query (SHQL)** and run:

```yaml
shql:
  from: hello-world
  where:
    - node:
        bind: ?person
        type: Person
  select:
    - ?person.id
    - ?person.label
  order_by: ?person.label
```

4. Ask the [AI Chat](help:help-ai-chat) panel a question about the data (an administrator must first configure a vendor and model).

Next: learn the model in [Hypernodes](help:help-hypernodes) and [Hyperedges](help:help-hyperedges), or the query language in the [SHQL overview](help:help-shql-overview).
