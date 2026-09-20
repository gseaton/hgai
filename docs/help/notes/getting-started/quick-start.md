---
id: help-quick-start
label: Quick Start
name: quick-start
description: Get a HypergraphAI server running, log in, and load the example hypergraphs.
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
docker-compose exec hgai python scripts/seed_data.py   # optional: load the example hypergraphs
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
python scripts/seed_data.py     # optional: load the example hypergraphs from scripts/seeds/
```

The Web UI is then at `http://localhost:8357/ui/`. See [Running locally](help:help-running-locally) for ports, multiple parallel servers, and options.

## Log in

The default administrator is **admin** with password **pwd357**. **Change this password immediately** (Accounts screen) — see [Accounts and roles](help:help-accounts-roles).

## The example hypergraphs

The example data lives in **`scripts/seeds/`** as ordinary hypergraph export files (`hgai-hypergraph-<id>.export.yml`), which the Docker image also contains. `scripts/seed_data.py` imports them into the running server:

| Seed | Contents |
|---|---|
| **`hello-world`** | 30 hypernodes and 16 hyperedges: the Three Stooges, the Rat Pack and the Beatles as `Group` nodes with `Person` members. `rel:member` edges carry `valid_from`/`valid_to` for each lineup, `rel:lineup` edges collect a group's lineups, and axiom edges declare `owl:inverse-of` (`rel:member` / `rel:member-of`). |
| **`eden`** | 9 hypernodes and 8 hyperedges: a small family tree (Adam, Eve, Cain, Abel, Seth, Enosh, Enoch) with `rel:parent`, `rel:child` and `rel:sibling` edges and inverse-of / transitive axioms. |

```bash
python scripts/seed_data.py               # load every seed
python scripts/seed_data.py eden          # just one, by graph id
python scripts/seed_data.py --list        # show what is available
```

Loading is safe to repeat: existing hypergraphs are merged into and nothing is overwritten. You can also import the same files from **Hypergraphs → Import** or with `import -f` in the [shell](help:help-shell) ([Exporting and importing hypergraphs](help:help-export-import)). Most documentation examples use these two graphs.

## Try something

1. Open **Hypergraphs**, then browse `hello-world`'s **Hypernodes** and **Hyperedges**.
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
