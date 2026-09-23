# HypergraphAI (hgai)

**HypergraphAI** is a hybrid semantic hypergraph document enterprise data platform. It combines the semantic expressiveness of knowledge graphs, the flexibility of document databases, and the power of hypergraph logic — engineered for alignment with AI agents and humans alike.

> MIT License | Python 3.11+ | FastAPI | MongoDB | MCP (Model Context Protocol)

---

## Table of Contents

- [Overview](#overview)
- [Key Concepts](#key-concepts)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
  - [Authentication Methods](#authentication-methods)
- [Running Locally](#running-locally)
- [Docker Deployment](#docker-deployment)
- [API Reference](#api-reference)
- [MCP Server](#mcp-server)
  - [Discovering Available Tools](#discovering-available-tools)
  - [MCP Tool Payload Examples](#mcp-tool-payload-examples)
    - [Get a Hypernode](#get-a-hypernode)
- [hgai Shell](#hgai-shell)
- [Web UI](#web-ui)
- [RDF Import](#rdf-import)
- [Inferencing](#inferencing)
- [SHQL — Semantic Hypergraph Query Language](#shql--semantic-hypergraph-query-language)
- [Module Development](#module-development)
- [Administration](#administration)
  - [MongoDB Indexes](#mongodb-indexes)
  - [Performance](#performance)
    - [Graph-scoped cache invalidation](#graph-scoped-cache-invalidation)
    - [Shared HTTP client](#shared-http-client)

---

## Overview

HypergraphAI stores and queries knowledge as **hypergraphs** — structures where a single hyperedge can connect _n_ nodes simultaneously (unlike ordinary graph edges limited to 2 nodes). This maps naturally to how humans and AI agents think about relationships.

Key differentiators:
- **Hyperedges are first-class entities** — edges have their own document-based attributes and can participate in other edges
- **Semantic relationships** — SKOS-based inferencing (`broader`, `narrower`, `related`)
- **Temporal awareness** — point-in-time (PIT) queries across the full history of your knowledge graph
- **AI-native** — all operations exposed as MCP (Model Context Protocol) server tools for AI agent integration
- **Modular** — all subsystems (security, core ops, inferencing) are pluggable modules
- **RBAC** — role-based access control for all operations

---

## Key Concepts

### Hypernode
A **hypernode** represents an entity (noun) with flexible document-based attributes. Every hypernode has:
- `id` — human-readable identifier
- `label` — display label
- `type` — entity type (e.g., `Person`, `Organization`, `Concept`)
- `attributes` — arbitrary JSON document
- `tags` — list of string tags
- `status` — `active`, `draft`, or `archived`
- Temporal fields: `valid_from`, `valid_to`

### Hyperedge
A **hyperedge** is a first-class semantic relationship that connects _n_ hypernodes. Key properties:
- `relation` — semantic relation type (e.g., `rel:member`, `rel:sibling`, `skos:broaderTransitive`)
- `members` — ordered list of participating hypernodes with optional roles
- `flavor` — relationship pattern: `hub`, `symmetric`, `direct`, `transitive`, `inverse-transitive`
- `attributes` — arbitrary JSON document
- `hyperkey` — SHA-256 hash ID generated from the normalized edge structure

### Hypergraph
A **hypergraph** is a named container for hypernodes and hyperedges. Hypergraphs can be:
- **Instantiated** — physical collections in MongoDB
- **Logical** — virtual compositions of one or more other hypergraphs (local or remote)

### Query Language (SHQL)
HypergraphAI queries are written in SHQL — a SPARQL-inspired, YAML-based pattern-matching language. Every query starts with the `shql:` key, matches `node`/`edge` patterns against `?variable` bindings (a variable shared across patterns is an implicit join), and projects the fields you want with `select:`:

```yaml
shql:
  from: hello-world
  where:
    - edge:
        bind: ?e
        relation: rel:member
  select:
    - ?e.label
    - ?e.members
    - ?e.valid_from
  as: result
```

Node and edge patterns accept standard MongoDB query operators (`$lt`, `$lte`, `$gt`, `$gte`, `$ne`, `$in`, `$all`, `$regex`, ...) directly inside `attributes:`, and the top-level boolean operators `$or`/`$and`/`$nor`/`$not` pass through unchanged — the engine maps any unrecognized key straight to the underlying MongoDB query document. See [Node Pattern](#node-pattern) and [Filter Expressions](#filter-expressions) below for the full syntax, including the `?var.field OP value` FILTER form for expressing the same comparisons over an already-bound variable.

See [SHQL — Semantic Hypergraph Query Language](#shql--semantic-hypergraph-query-language) further down for the complete language reference — variables, node/edge patterns, OPTIONAL/UNION, point-in-time queries, aggregation, inferencing, and a full worked-example gallery. The rest of this section walks through one representative query to show variable binding and implicit joins end to end.

Given a `rel:president-of` hyperedge whose members are `[nation:usa, person:<president>]` (seq 0 = the president), resolve the sitting president's full node record as of a given date:

```yaml
shql:
  from:
    - hg-alpha
    - hg-bravo
  at: "1948-11-22T00:00:00Z"
  where:
    # Match the president-of hyperedge that contains nation:usa as a member
    - edge: ?potus_edge
      relation: rel:president-of
      members:
        - node_id: nation:usa        # anchors the edge to the USA
        - node_id: ?president_id     # binds the other member (the president)
          seq: 0

    # Join to the Person node using the bound ?president_id
    - node: ?president
      id: ?president_id
      node_type: Person

  select:
    - ?president.id
    - ?president.label
    - ?president.description
    - ?president.attributes

  as: potus-at
```

How it works:

| Step | Pattern | Effect |
|---|---|---|
| 1 | `edge: ?potus_edge` with `nation:usa` member | Finds edges where `nation:usa` is a member, binding the edge doc to `?potus_edge` |
| 2 | `node_id: ?president_id` + `seq: 0` | Binds the seq-0 member's node ID to `?president_id` |
| 3 | `node: ?president` + `id: ?president_id` | Resolves `?president_id` to a node lookup, binding the full Person doc to `?president` |
| 4 | `select` | Projects `id`, `label`, `description`, `attributes` from the bound Person |

The `at:` timestamp is respected at every stage — both the edge lookup and node lookup are evaluated at the point-in-time `1948-11-22`, so the result reflects whoever held the office on that date.

Step 2's `seq: 0` is enforced positionally: `?president_id` only binds to the member whose `seq` is actually `0` on that edge, not just any unused member — see [Edge Pattern](#edge-pattern) and worked example #13 ([Positional member filter](#13-positional-member-filter--find-the-first-member-by-seq)) below for the full mechanics. If the edge's seq-0 slot were occupied by someone other than the president (a malformed edge), the pattern would fail to match rather than binding the wrong node.

For the complete set of member-matching, filtering, aggregation, and inferencing examples (attribute filters, `$in`/`$all`-style membership tests, numeric/boolean operators, positional `seq` filters, aggregation, axiom-driven inferencing), see the worked-example gallery under [SHQL — Semantic Hypergraph Query Language § Examples](#examples) further down.

### Space-scoped Graph References

Graphs owned by a space are referenced with a slash separator: `space_id/graph_id`. This distinguishes space-scoped graphs from unowned graphs and from mesh dot-notation refs.

| `from:` value | Meaning |
|---|---|
| `my-graph` | Unowned local graph (`space_id` is null) |
| `alpha/alpha-hg` | Graph `alpha-hg` scoped to space `alpha` |

Query all nodes in a space-scoped graph:

```yaml
shql:
  from: alpha/alpha-hg
  where:
    - node: ?n
  select:
    - ?n.id
    - ?n.label
    - ?n.type
    - ?n.attributes
```

`from:` accepts a list mixing space-scoped, unowned, and mesh dot-notation refs in any combination, and `at:` (point-in-time) works identically whether or not a graph is space-scoped. See worked examples [#8–12](#8-find-all-nodes-in-a-space-scoped-graph) under [SHQL — Semantic Hypergraph Query Language § Examples](#examples) for multi-space queries, mixing a space graph with an unowned one, PIT on a space graph, and the 4-component mesh dot-notation `mesh.server.space.graph` for remote space-scoped graphs.

---

## Architecture

```
hgai/
├── hgai/                        # Core Python package
│   ├── main.py                  # FastAPI app, lifespan, module mounts
│   ├── config.py                # pydantic-settings (HGAI_ prefix)
│   ├── db/storage.py            # storage backend accessor (get_storage, init_storage)
│   ├── models/                  # Pydantic models: hypernode, hyperedge, hypergraph, account
│   ├── core/                    # Core engine: CRUD, inference, auth, cache
│   └── api/routers/             # auth, hypergraphs, hypernodes, hyperedges, accounts
│
├── hgai_module_storage/         # Storage abstraction — backend ABCs and filter types
│   ├── backend.py               # StorageBackend ABC + per-entity Store ABCs
│   ├── filters.py               # Typed filter/patch dataclasses
│   ├── exceptions.py            # StorageError, NotFoundError, ConflictError
│   └── registry.py              # Backend registration and discovery
│
├── hgai_module_storage_mongodb/ # MongoDB storage backend (default)
│   ├── backend.py               # MongoStorageBackend(StorageBackend)
│   ├── connection.py            # AsyncIOMotorClient lifecycle
│   ├── indexes.py               # All collection index definitions
│   └── stores/                  # Per-entity store implementations
│
├── hgai_module_shql/            # SHQL — Semantic Hypergraph Query Language module
│   ├── parser.py                # parse_shql() + validate_shql()
│   ├── engine.py                # execute_shql() — binding sets, pattern evaluation, projection
│   └── api_router.py            # POST /api/v1/shql/query, /validate, /cache/invalidate
│
├── hgai_module_mesh/            # Mesh — distributed server registry + federation module
│   ├── models.py                # MeshServer, MeshCreate, MeshUpdate, MeshResponse
│   ├── engine.py                # ping, sync, federated SHQL
│   └── api_router.py            # CRUD + /ping, /sync, /query endpoints
│
├── hgai_module_mcp/             # MCP — Model Context Protocol module
│   └── server.py                # FastMCP server: 14 tools (CRUD + SHQL query + inferencing)
│
├── ui/                          # Web UI (SPA, vanilla JS + Bootstrap)
├── shell/                       # hgai interactive CLI shell
├── scripts/                     # MongoDB cold-start and seed scripts
│   └── seeds/                   # Example hypergraphs as export YAML files (hello-world, eden)
├── tests/                       # pytest test suite
│   ├── test_engine.py           # Hyperkey tests
│   ├── test_shql.py             # SHQL member-pattern matching tests
│   ├── test_inference.py        # Inferencing primitives tests
│   └── test_mesh.py             # Mesh module tests
├── hgai.sh                      # Start the hgai server
├── shell.sh                     # Start the hgai interactive shell
└── docs/                        # Documentation
```

### Storage Backends

HypergraphAI uses a pluggable storage backend system. The default backend is MongoDB, implemented in `hgai_module_storage_mongodb`. All storage access goes through the abstract interface in `hgai_module_storage` — no module outside the storage modules imports MongoDB or Motor directly.

**Built-in backends:**

| Backend name | Module | Description |
|---|---|---|
| `mongodb` | `hgai_module_storage_mongodb` | Default. MongoDB 7+ via Motor async driver. |

**Selecting a backend:**
```bash
HGAI_STORAGE_BACKEND=mongodb   # (default)
```

**Implementing a custom backend:**

Create a Python package that:
1. Defines a class inheriting from `hgai_module_storage.backend.StorageBackend`
2. Implements all per-entity Store ABCs (`HypergraphStore`, `HypernodeStore`, etc.)
3. Calls `register_backend("myname", MyBackend)` from `hgai_module_storage.registry` on import

Then set `HGAI_STORAGE_BACKEND=myname` and ensure your module is imported at startup.

See `hgai_module_storage_mongodb/` for the reference implementation and `hgai_module_storage/backend.py` for the full interface.

---

### Docker (recommended)
```bash
cp .env.example .env
docker-compose up -d
python scripts/seed_data.py     # load the example hypergraphs from scripts/seeds/ (hello-world, eden)
```

- Web UI: http://localhost:8000/ui/ — login: admin / pwd357
- API docs: http://localhost:8000/api/docs
- MCP server: http://localhost:8000/mcp/

### Local dev
```bash
./hgai.sh                                           # start server (default port 8357)
./hgai.sh --port 9000                               # custom port
./hgai.sh --mongo-db mydb --server-id my-server     # full options
```

- Web UI: http://localhost:8357/ui/ — login: admin / pwd357
- API docs: http://localhost:8357/api/docs
- MCP server: http://localhost:8357/mcp/

### Shell
```bash
./shell.sh                                                    # connect to localhost:8357
./shell.sh --server http://localhost:8357 --user admin        # explicit connection
./shell.sh --server http://myserver:8357 -u myuser -p mypass  # remote server
```

### Component Layers

```
┌─────────────────────────────────────────────────────┐
│                    Web UI / hgai Shell               │
├─────────────────┬───────────────────────────────────┤
│   REST API      │         MCP Server Tools           │
│  (FastAPI)      │         (FastMCP)                  │
├─────────────────┴───────────────────────────────────┤
│              Core Engine                             │
│  query | inference | auth | cache | temporal         │
├─────────────────────────────────────────────────────┤
│              MongoDB (motor async)                   │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- MongoDB 7+ (or use Docker)

### 1. Clone and configure

```bash
git clone <repo-url>
cd hgai
cp .env.example .env
# Edit .env as needed
```

### 2. Start with Docker Compose

```bash
docker-compose up -d
```

This starts:
- **MongoDB** on port 27017
- **HypergraphAI server** on port 8000
- UI at http://localhost:8000/ui/
- API at http://localhost:8000/api/v1/
- MCP server at http://localhost:8000/mcp/

### 3. Default credentials

| Account | Username | Password |
|---------|----------|----------|
| Admin   | `admin`  | `pwd357` |

### 4. Seed the example hypergraphs

```bash
docker-compose exec hgai python scripts/seed_data.py
```

The seeds are **ordinary hypergraph export files** in [`scripts/seeds/`](scripts/seeds/) (also copied into the Docker image with the rest of `scripts/`) — nothing is hard-coded in the loader:

| File | Hypergraph |
|------|------------|
| `hgai-hypergraph-hello-world.export.yml` | `hello-world` — 30 hypernodes / 16 hyperedges: the Three Stooges, Rat Pack and Beatles, with temporal lineup edges and inverse-of / broader axioms |
| `hgai-hypergraph-eden.export.yml` | `eden` — 9 hypernodes / 8 hyperedges: a small family tree with parent/child/sibling edges and inverse-of / transitive axioms |

```bash
python scripts/seed_data.py                 # load every seed (safe to repeat: existing data is skipped, never overwritten)
python scripts/seed_data.py eden            # load one, by graph id ...
python scripts/seed_data.py ./my.export.yml # ... or any export file by path
python scripts/seed_data.py --list          # list the available seeds
```

The same files can be loaded from the Web UI (**Hypergraphs → Import**) or the shell (`import -f scripts/seeds/hgai-hypergraph-eden.export.yml`). To add or change a seed, add or edit an export file in `scripts/seeds/` (see the export/import section under [Web UI](#web-ui)).

---

## Configuration

All configuration is via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `HGAI_STORAGE_BACKEND` | `mongodb` | Storage backend name (`mongodb` is the only built-in backend) |
| `HGAI_MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection URI (used by `mongodb` backend) |
| `HGAI_MONGO_DB` | `hgai` | MongoDB database name (used by `mongodb` backend) |
| `HGAI_SECRET_KEY` | *(required)* | JWT signing secret |
| `HGAI_TOKEN_EXPIRE_MINUTES` | `480` | JWT token lifetime |
| `HGAI_PRIMARY_API_KEY` | *(none)* | Primary API key for machine-to-machine auth |
| `HGAI_SECONDARY_API_KEY` | *(none)* | Secondary API key (for key rotation) |
| `HGAI_HOST` | `0.0.0.0` | Server bind host |
| `HGAI_PORT` | `8357` | Server bind port |
| `HGAI_LOG_LEVEL` | `info` | Log level |
| `HGAI_CACHE_TTL_SECONDS` | `300` | Query cache TTL |
| `HGAI_CACHE_ENABLED` | `true` | Enable query caching |
| `HGAI_SERVER_ID` | `hgai-local` | Server identifier (for meshes) |
| `HGAI_SERVER_NAME` | `HypergraphAI Local` | Server display name |
| `HGAI_HELP_DIR` | `<project>/docs/help` | Root of the built-in Help content (`notes/` markdown topics, `media/` files) |

### Authentication Methods

HypergraphAI supports two authentication methods:

#### 1. JWT Tokens (User Authentication)

For interactive users and web UI access. Obtain a token via the login endpoint:

```bash
curl -X POST http://localhost:8357/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=pwd357"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800
}
```

Use the token in subsequent requests:
```bash
curl http://localhost:8357/api/v1/graphs \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 2. API Keys (Machine-to-Machine Authentication)

For AI agents, MCP clients, and automated systems. API keys are stateless and do not require a login step — they grant full admin access.

**Setup:**

Generate a secure API key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Add to your `.env` file:
```bash
HGAI_PRIMARY_API_KEY=your-generated-api-key-here
HGAI_SECONDARY_API_KEY=optional-second-key-for-rotation
```

**Usage:**

Use the API key directly as a Bearer token:
```bash
curl http://localhost:8357/api/v1/graphs \
  -H "Authorization: Bearer your-generated-api-key-here"
```

**MCP Client Configuration:**

Configure Claude Desktop or other MCP clients with the API key:
```json
{
  "mcpServers": {
    "hgai": {
      "url": "http://localhost:8357/mcp/",
      "headers": {
        "Authorization": "Bearer your-generated-api-key-here"
      }
    }
  }
}
```

**Key Rotation:**

Two API keys are supported (`PRIMARY` and `SECONDARY`) to enable zero-downtime key rotation:
1. Generate a new key and set it as `HGAI_SECONDARY_API_KEY`
2. Update clients to use the new key
3. Move the new key to `HGAI_PRIMARY_API_KEY` and remove the old key

---

## Running Locally

### ENV VARS

Environment variables used if not overridden using command-line overrides

- `HGAI_PORT` : defaults to 8357
- `HGAI_MONGO_URI` : default MongoDB connection string
- `HGAI_MONGO_DB` : default MongoDB hgai database name (common 'hgai')
- `HGAI_SERVER_ID` : default hgai server id (used in meshes)
- `HGAI_SERVER_NAME` : default hgai server name (used in meshes)

```bash
# Defaults to port=8357; mongo-db=hgai 
$ ./hgai.sh

# Starting parallel local hgai servers
$ ./hgai.sh --port 8361 --server-id hgai-alpha --mongo-db hgai_alpha --server-name HypergaphAI-Alpha
$ ./hgai.sh --port 8362 --server-id hgai-bravo --mongo-db hgai_bravo --server-name HypergaphAI-Bravo
```

```bash
# Install dependencies
pip install -r requirements.txt

# Start MongoDB (or use Docker)
docker run -d -p 27017:27017 --name hgai-mongo \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=pwd357 \
  mongo:7

# Initialize MongoDB
mongosh --username admin --password pwd357 \
  --authenticationDatabase admin < scripts/mongo-init.js

# Set environment
cp .env.example .env

# Run the server
./hgai.sh

# Seed data (optional)
python scripts/seed_data.py
```

---

## Docker Deployment

```bash
# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f hgai

# Stop
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

---

## API Reference

See [docs/api-reference.md](docs/api-reference.md) for full API documentation.

Base URL: `http://localhost:8357/api/v1`

### Authentication
```
POST /api/v1/auth/token        # Login (returns JWT)
GET  /api/v1/auth/me           # Current user info
```

### Hypergraphs
```
GET    /api/v1/graphs                  # List hypergraphs
POST   /api/v1/graphs                  # Create hypergraph
GET    /api/v1/graphs/{id}             # Get hypergraph
PUT    /api/v1/graphs/{id}             # Update hypergraph
DELETE /api/v1/graphs/{id}             # Delete hypergraph
GET    /api/v1/graphs/{id}/export?format=yaml   # Export to hgai-hypergraph-<id>-<timestamp>.export.yml
POST   /api/v1/graphs/import?mode=create|merge  # Import an export file (raw body) as a new/merged hypergraph
POST   /api/v1/graphs/import/rdf?graph_id=&format=&mode=  # Import RDF (Turtle/RDF-XML/JSON-LD/N3) — mapped to hypernodes + hyperedges
```

### Hypernodes
```
GET    /api/v1/graphs/{g}/nodes        # List hypernodes
POST   /api/v1/graphs/{g}/nodes        # Create hypernode
GET    /api/v1/graphs/{g}/nodes/{id}   # Get hypernode
PUT    /api/v1/graphs/{g}/nodes/{id}   # Update hypernode
DELETE /api/v1/graphs/{g}/nodes/{id}   # Delete hypernode
```

### Hyperedges
```
GET    /api/v1/graphs/{g}/edges        # List hyperedges
POST   /api/v1/graphs/{g}/edges        # Create hyperedge
GET    /api/v1/graphs/{g}/edges/{id}   # Get hyperedge
PUT    /api/v1/graphs/{g}/edges/{id}   # Update hyperedge
DELETE /api/v1/graphs/{g}/edges/{id}   # Delete hyperedge
```

### Inference
```
POST /api/v1/graphs/{g}/infer/transitive   # Single-pair/closure/path reachability over an owl:transitive relation
POST /api/v1/graphs/{g}/infer/expand       # Axiom-driven expansion of one hyperedge
POST /api/v1/graphs/{g}/infer/project      # Materialize inference results as persisted hyperedges
```

### Notes
```
GET    /api/v1/notes                          # List notes visible to the caller (own, shared, public)
POST   /api/v1/notes                          # Create a note
GET    /api/v1/notes/{id}                     # Get a note
PUT    /api/v1/notes/{id}                     # Update a note
DELETE /api/v1/notes/{id}                     # Delete a note
PUT    /api/v1/notes/{id}/scope               # Set the note's scope (private/protected/protected-edit/public/public-edit)
POST   /api/v1/notes/{id}/share               # Grant/replace an account's access
DELETE /api/v1/notes/{id}/share/{username}    # Revoke an account's access
```

### Help
```
GET /api/v1/help/topics              # List/search help topics (tags, search, skip, limit, sort)
GET /api/v1/help/home                # Landing topic (help-home)
GET /api/v1/help/topics/{id}         # One topic, with Markdown text
GET /api/v1/help/media/{path}        # Media file used by help topics
```

### Media
```
GET    /api/v1/media           # List media
POST   /api/v1/media           # Upload a file
GET    /api/v1/media/{id}      # Download a file
PUT    /api/v1/media/{id}      # Update metadata
DELETE /api/v1/media/{id}      # Delete a file
```

### Query
```
POST /api/v1/shql/query               # Execute SHQL query
POST /api/v1/shql/validate            # Validate SHQL (dry-run)
POST /api/v1/shql/cache/invalidate    # Flush the query result cache
```

### Accounts (admin only)
```
GET    /api/v1/accounts        # List accounts
POST   /api/v1/accounts        # Create account
GET    /api/v1/accounts/{id}   # Get account
PUT    /api/v1/accounts/{id}   # Update account
DELETE /api/v1/accounts/{id}   # Delete account
```

### Meshes (admin only)
```
GET    /api/v1/meshes                   # List meshes
POST   /api/v1/meshes                   # Create mesh
GET    /api/v1/meshes/{id}              # Get mesh
PUT    /api/v1/meshes/{id}              # Update mesh
DELETE /api/v1/meshes/{id}              # Delete mesh
GET    /api/v1/meshes/{id}/ping         # Health-check all servers in mesh
POST   /api/v1/meshes/{id}/sync         # Refresh graph lists from live remotes
POST   /api/v1/meshes/{id}/query        # Execute federated SHQL across all mesh servers
```

---

## MCP Server

HypergraphAI exposes all operations as MCP (Model Context Protocol) tools via the `hgai_module_mcp` module, mounted at:

```
http://localhost:8357/mcp/
```

Configure your MCP client (e.g., Claude Desktop):
```json
{
  "mcpServers": {
    "hgai": {
      "url": "http://localhost:8357/mcp/",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```

### Authorization

Every MCP tool call runs as the authenticated account and is checked with the same rules as the REST API: graph tools need access to the graph plus the `read` / `write` / `delete` operation, `hgai_query_execute` needs the `query` operation on every graph in `from:`, space tools need the matching space role, and `hgai_mesh_*` needs the `admin` role. A refused call returns `{"error": "...", "type": "PermissionDenied"}` as the tool result. API keys are full-admin credentials and bypass the checks — for a restricted agent, create a dedicated account and use its login token. Writes are audited under the caller's username.

### Discovering Available Tools

To get the list of all available MCP tools from the server, use the `tools/list` MCP method.

**Using curl:**
```bash
curl -X POST http://localhost:8357/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

**Example response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "hgai_hypergraph_list",
        "description": "List all HypergraphAI hypergraphs.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string",
              "description": "Filter by status ('active', 'archived', 'draft', or '' for all)"
            }
          }
        }
      },
      {
        "name": "hgai_hypernode_get",
        "description": "Get a hypernode by ID.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "graph_id": { "type": "string", "description": "The hypergraph identifier" },
            "node_id": { "type": "string", "description": "The hypernode identifier" }
          },
          "required": ["graph_id", "node_id"]
        }
      }
    ]
  }
}
```

**Using Python (mcp client):**
```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def list_tools():
    async with sse_client("http://localhost:8357/mcp/") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"{tool.name}: {tool.description}")

asyncio.run(list_tools())
```

**Calling a tool via MCP protocol:**
```bash
curl -X POST http://localhost:8357/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "hgai_hypernode_get",
      "arguments": {
        "graph_id": "hello-world",
        "node_id": "person:moe"
      }
    }
  }'
```

### MCP Tools

#### Hypergraph Tools

| Tool | Description |
|------|-------------|
| `hgai_hypergraph_list` | List all hypergraphs, filtered by status (`active`, `archived`, `draft`, or all) |
| `hgai_hypergraph_get` | Get a hypergraph by ID |
| `hgai_hypergraph_stats` | Get node/edge counts and statistics for a hypergraph |
| `hgai_hypergraph_create` | Create a new hypergraph (`instantiated` or `logical`) |

#### Hypernode Tools

| Tool | Description |
|------|-------------|
| `hgai_hypernode_list` | List hypernodes in a graph, filtered by type and/or tags |
| `hgai_hypernode_get` | Get a hypernode by ID |
| `hgai_hypernode_create` | Create a new hypernode with type, attributes, and tags |
| `hgai_hypernode_update` | Update a hypernode's label, attributes, tags, or status |
| `hgai_hypernode_delete` | Delete a hypernode |

#### Hyperedge Tools

| Tool | Description |
|------|-------------|
| `hgai_hyperedge_list` | List hyperedges in a graph, filtered by relation type or member node ID |
| `hgai_hyperedge_get` | Get a hyperedge by ID or hyperkey |
| `hgai_hyperedge_create` | Create a new n-ary hyperedge connecting any number of hypernodes |
| `hgai_hyperedge_delete` | Delete a hyperedge |

#### Query Tools

| Tool | Description |
|------|-------------|
| `hgai_query_execute` | Execute an SHQL query (top-level `shql:` key) |
| `hgai_query_validate` | Validate an SHQL query without executing it |

#### Inference Tools

| Tool | Description |
|------|-------------|
| `hgai_infer_expand_edge` | Axiom-driven expansion (inverse-of/symmetric/superproperty/transitive) of one hyperedge |
| `hgai_infer_check_transitive` | Single-pair/closure/path reachability over a relation carrying an `owl:transitive` axiom |

#### Mesh Tools

| Tool | Description |
|------|-------------|
| `hgai_mesh_list` | List configured meshes |
| `hgai_mesh_get` | Get a mesh's configuration |
| `hgai_mesh_ping` | Check reachability of a mesh's servers |
| `hgai_mesh_sync` | Sync graph listings from a mesh's servers |
| `hgai_mesh_query` | Execute a federated SHQL query across a mesh's servers |

#### Media Tools

| Tool | Description |
|------|-------------|
| `hgai_media_upload` | Upload a media file |
| `hgai_media_download` | Download a media file |
| `hgai_media_delete` | Delete a media file |

#### Space Tools

| Tool | Description |
|------|-------------|
| `hgai_space_list` | List spaces |
| `hgai_space_get` | Get a space's details and members |
| `hgai_space_create` | Create a space |
| `hgai_space_add_member` | Add or update a space member |
| `hgai_space_list_graphs` | List hypergraphs in a space |

### Tool Reference

#### `hgai_hypergraph_create`
```
id          Unique identifier (slug format recommended)
label       Human-readable display label
description Optional description
graph_type  'instantiated' (physical) or 'logical' (composed)
tags        Comma-separated tags
```

#### `hgai_hypernode_create`
```
graph_id         Target hypergraph ID
id               Unique node ID within the hypergraph
label            Display label
node_type        Entity type: 'Person', 'Organization', 'Concept', 'RelationType', etc.
attributes_json  JSON string of document attributes, e.g. '{"city": "Paris"}'
tags             Comma-separated tags
description      Optional description
```

#### `hgai_hypernode_update`
```
graph_id         Hypergraph ID
node_id          Node ID to update
label            New label (optional)
attributes_json  New attributes as JSON string (optional, replaces existing)
tags             New comma-separated tags (optional)
status           New status: 'active', 'draft', or 'archived' (optional)
```

#### `hgai_hyperedge_create`
```
graph_id         Target hypergraph ID
relation         Semantic relation type: 'rel:member', 'rel:sibling', 'skos:broaderTransitive', etc.
members_json     JSON array: [{"node_id": "id", "seq": 0}, ...]
edge_id          Optional human-readable ID (hyperkey auto-generated if omitted)
label            Optional display label
flavor           'hub', 'symmetric', 'direct', 'transitive', or 'inverse-transitive'
attributes_json  JSON document of edge attributes
tags             Comma-separated tags
```

#### `hgai_query_execute`
```
query_yaml  SHQL query in YAML format — top-level 'shql:' key
use_cache   Whether to use query result cache (default: true)
```

Example:
```yaml
shql:
  from: hello-world
  where:
    - edge:
        bind: ?e
        relation: rel:member
        members:
          - node_id: group:three-stooges
          - node_id: ?person_id
    - node:
        bind: ?stooge
        id: ?person_id
        type: Person
  select:
    - ?stooge.label
```

### MCP Tool Payload Examples

These examples show the JSON payloads for common MCP server tool calls. Use these with your MCP client or via the MCP protocol.

#### List Hypergraphs

```json
{
  "name": "hgai_hypergraph_list",
  "arguments": {
    "status": "active"
  }
}
```

#### Get a Hypergraph

```json
{
  "name": "hgai_hypergraph_get",
  "arguments": {
    "graph_id": "hello-world"
  }
}
```

#### Get Hypergraph Statistics

```json
{
  "name": "hgai_hypergraph_stats",
  "arguments": {
    "graph_id": "hello-world"
  }
}
```

#### Create a Hypergraph

```json
{
  "name": "hgai_hypergraph_create",
  "arguments": {
    "id": "my-knowledge-graph",
    "label": "My Knowledge Graph",
    "description": "A hypergraph for storing project knowledge",
    "graph_type": "instantiated",
    "tags": "project,knowledge"
  }
}
```

#### List Hypernodes

```json
{
  "name": "hgai_hypernode_list",
  "arguments": {
    "graph_id": "hello-world",
    "node_type": "Person",
    "tags": "",
    "skip": 0,
    "limit": 50
  }
}
```

#### Get a Hypernode

Fetch a single hypernode by its ID within a hypergraph.

**curl:**
```bash
curl -s -X POST http://localhost:8357/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "hgai_hypernode_get",
      "arguments": {
        "graph_id": "hello-world",
        "node_id": "person:moe"
      }
    }
  }'
```

**Python (MCP streamable HTTP client):**
```python
import asyncio
import json
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

async def get_node(graph_id: str, node_id: str):
    async with streamablehttp_client(
        "http://localhost:8357/mcp/",
        headers={"Authorization": "Bearer <your-api-key>"},
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "hgai_hypernode_get",
                {"graph_id": graph_id, "node_id": node_id},
            )
            node = json.loads(result.content[0].text)
            return node

node = asyncio.run(get_node("hello-world", "person:moe"))
print(node)
```

**Example response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"id\": \"person:moe\", \"graph_id\": \"hello-world\", \"label\": \"Moe\", \"type\": \"Person\", \"description\": \"Moe Howard\", \"attributes\": {}, \"tags\": [], \"status\": \"active\", \"valid_from\": null, \"valid_to\": null}"
      }
    ]
  }
}
```

If the node does not exist, the tool returns `{"error": "Node '<node_id>' not found in graph '<graph_id>'"}` inside the `text` field (HTTP 200 — errors are returned as tool output, not HTTP errors).

#### Create a Hypernode

```json
{
  "name": "hgai_hypernode_create",
  "arguments": {
    "graph_id": "hello-world",
    "id": "person:john-doe",
    "label": "John Doe",
    "node_type": "Person",
    "attributes_json": "{\"born\": \"1990-05-15\", \"city\": \"New York\"}",
    "tags": "employee,developer",
    "description": "A software developer"
  }
}
```

#### Update a Hypernode

```json
{
  "name": "hgai_hypernode_update",
  "arguments": {
    "graph_id": "hello-world",
    "node_id": "person:john-doe",
    "label": "John A. Doe",
    "attributes_json": "{\"born\": \"1990-05-15\", \"city\": \"San Francisco\", \"role\": \"Senior Developer\"}",
    "tags": "employee,developer,senior",
    "status": "active"
  }
}
```

#### Delete a Hypernode

```json
{
  "name": "hgai_hypernode_delete",
  "arguments": {
    "graph_id": "hello-world",
    "node_id": "person:john-doe"
  }
}
```

#### List Hyperedges

```json
{
  "name": "hgai_hyperedge_list",
  "arguments": {
    "graph_id": "hello-world",
    "relation": "rel:member",
    "node_id": "",
    "skip": 0,
    "limit": 50
  }
}
```

#### Get a Hyperedge

```json
{
  "name": "hgai_hyperedge_get",
  "arguments": {
    "graph_id": "hello-world",
    "edge_id": "three-stooges-classic-lineup"
  }
}
```

#### Create a Hyperedge

```json
{
  "name": "hgai_hyperedge_create",
  "arguments": {
    "graph_id": "hello-world",
    "relation": "rel:member",
    "members_json": "[{\"node_id\": \"team:engineering\", \"seq\": 0}, {\"node_id\": \"person:john-doe\", \"seq\": 1}, {\"node_id\": \"person:jane-smith\", \"seq\": 2}]",
    "edge_id": "engineering-team-members",
    "label": "Engineering Team Members",
    "flavor": "hub",
    "attributes_json": "{\"department\": \"Engineering\", \"formed\": \"2024-01-15\"}",
    "tags": "team,membership"
  }
}
```

#### Delete a Hyperedge

```json
{
  "name": "hgai_hyperedge_delete",
  "arguments": {
    "graph_id": "hello-world",
    "edge_id": "engineering-team-members"
  }
}
```

#### Execute an SHQL Query

```json
{
  "name": "hgai_query_execute",
  "arguments": {
    "query_yaml": "shql:\n  from: hello-world\n  where:\n    - edge:\n        bind: ?membership\n        relation: rel:member\n        members:\n          - node_id: group:three-stooges\n          - node_id: ?person_id\n    - node:\n        bind: ?person\n        id: ?person_id\n        type: Person\n  select:\n    - ?person.id\n    - ?person.label\n    - ?membership.label\n  limit: 100",
    "use_cache": true
  }
}
```

#### Validate a Query

```json
{
  "name": "hgai_query_validate",
  "arguments": {
    "query_yaml": "shql:\n  from: hello-world\n  where:\n    - edge:\n        relation: rel:member\n  select:\n    - \"*\""
  }
}
```

#### List Meshes

```json
{
  "name": "hgai_mesh_list",
  "arguments": {}
}
```

#### Get a Mesh

```json
{
  "name": "hgai_mesh_get",
  "arguments": {
    "mesh_id": "alpha-bravo-mesh"
  }
}
```

#### Ping Mesh Servers

```json
{
  "name": "hgai_mesh_ping",
  "arguments": {
    "mesh_id": "alpha-bravo-mesh"
  }
}
```

#### Federated Mesh Query

```json
{
  "name": "hgai_mesh_query",
  "arguments": {
    "mesh_id": "alpha-bravo-mesh",
    "query_yaml": "shql:\n  from: alpha-bravo-mesh\n  where:\n    - node:\n        bind: ?person\n        type: Person\n  select:\n    - ?person.id\n    - ?person.label\n    - ?person.attributes\n  limit: 100",
    "use_cache": true
  }
}
```

---

## hgai Shell

The `hgai` shell provides an interactive CLI for all HypergraphAI operations:

```bash
./hgsh.sh
```

Or connect to a remote server:
```bash
./hgsh.sh --server http://myserver:8357 --user admin
```

### hgsh Shell Commands

```
connect <url> [-u user] [-p]   Connect to a HypergraphAI server
disconnect                      Disconnect from server
use <graph-id>                  Set active hypergraph
whoami                          Show current user

ls graphs                       List hypergraphs
ls nodes                        List hypernodes in active graph
ls edges                        List hyperedges in active graph

get node <id>                   Get a hypernode
get edge <id>                   Get a hyperedge
get graph <id>                  Get a hypergraph

create node                     Create hypernode (opens YAML editor)
create edge                     Create hyperedge (opens YAML editor)
create graph                    Create hypergraph

update node <id>                Update hypernode
update edge <id>                Update hyperedge

delete node <id>                Delete hypernode
delete edge <id>                Delete hyperedge

shql                            Run SHQL query (paste YAML, end with EOF)
shql -f <file>                  Run SHQL query from file

import -f <file> [-g id] [--merge]  Import a hypergraph from an export file
import-rdf -f <file> [-g id] [--format ttl|n3|rdf|xml|jsonld] [--merge]  Import an RDF file (Turtle/RDF-XML/JSON-LD/N3)
export [-o <file>] [-g id]          Export a hypergraph to hgai-hypergraph-<id>-<timestamp>.export.yml

help [command]                  Show help
exit                            Exit shell
```

---

## Web UI

The web UI is served at `http://localhost:8357/ui/` (local dev) or `http://localhost:8000/ui/` (Docker) and provides:

- **Login** — secure authentication
- **Dashboard** — graph overview with counts and activity
- **Hypergraphs** — list and manage hypergraphs; **Export** any hypergraph to a `hgai-hypergraph-<id>-<timestamp>.export.yml` file and **Import** such a file — or an RDF file (Turtle/RDF-XML/JSON-LD/N3, see [RDF Import](#rdf-import)) — into this or another instance (optionally into a space, under a new id, or merged into an existing graph)
- **Hypernodes** — full CRUD with attribute editing
- **Hyperedges** — full CRUD with member management
- **Query** — interactive SHQL query editor with results visualization
- **Help** — searchable documentation with tag-based virtual folders, landing on `docs/help/notes/home.md`; built from markdown files with front matter under `docs/help/notes/` and from any Note tagged `system:help`. The AI Chat agent reads the same topics to answer questions about HypergraphAI. See [docs/help](docs/help/notes/home.md) and the *Adding your own help topics* topic.
- **Admin** — account management, server info (admin role only)

---

## RDF Import

HypergraphAI can import an existing RDF file — **Turtle** (`.ttl`), **RDF/XML** (`.rdf`, `.xml`), **JSON-LD** (`.jsonld`) or **Notation3** (`.n3`) — mapping every triple onto hypernodes and hyperedges. RDF has no native n-ary relationships, so the mapping is deliberately simple: every triple becomes one two-member hyperedge.

```bash
curl -X POST "http://localhost:8357/api/v1/graphs/import/rdf?graph_id=my-graph&format=ttl" \
  -H "Authorization: Bearer $TOKEN" --data-binary @data.ttl
```

```bash
./hgsh.sh
> import-rdf -f data.ttl -g my-graph   # format inferred from the extension if omitted
```

### Mapping model

| RDF | Becomes |
|---|---|
| A subject, or a resource-valued object (IRI or blank node, never a literal) | A **hypernode**; id = the term's **full, expanded IRI** (`ex:adam` with `@prefix ex: <http://example.com/>` becomes `http://example.com/adam` — never left as the compact CURIE). A blank node's id is `bnode:<label>` |
| `rdf:type` | The hypernode's `type` (first type's short local name) and the full expanded-IRI list in `attributes.rdf_type` |
| A label (`rdfs:label`, `skos:prefLabel`, `foaf:name`, `dc:title`, `dcterms:title`, in that order) | The hypernode's `label`, else the IRI's local name |
| Any other literal-valued triple | An attribute keyed by a compact `prefix:local` CURIE (`attributes["foaf:age"]`) — **not** expanded (an attribute key is a MongoDB field name; expanding it would break SHQL's `attributes: {key: value}` dot-path filter). The **value** is classified by its own lexical text: starts with a digit → a number (`int` if it parses as one, else `float`; `-1` if neither parses — even for a value RDF typed as a plain string, e.g. `"12345"`); anything else → text. Booleans and dates/timestamps keep native conversion regardless |
| A resource-valued triple | A `hub` hyperedge: `relation` = the predicate's full expanded IRI, `members` = `[subject (seq 0), object (seq 1)]` |
| `<P> a owl:TransitiveProperty` | *(additional to `rdf:type` above)* a `hub` hyperedge: `relation` = `owl:transitive`, `members` = `[<P> (seq 0)]` — recognized by `infer: true` exactly like a hand-asserted axiom edge |
| `<P> owl:inverseOf <Q>` | A `hub` hyperedge: `relation` = `owl:inverse-of` (HypergraphAI's own spelling — not the real predicate's CURIE `owl:inverseOf`), `members` = `[<P> (seq 0), <Q> (seq 1)]` |
| `<P> a owl:SymmetricProperty` | Two things: every data triple using `<P>` gets flavor `symmetric` instead of `hub` (reads both directions with no `infer: true` needed), plus a `hub` axiom hyperedge: `relation` = `owl:symmetric`, `members` = `[<P> (seq 0)]`, recognized by `infer: true` |

**Not handled** (round-trips as ordinary triples/attributes instead): RDF Collections (`rdf:first`/`rdf:rest`), JSON-LD named graphs (merged into one triple set), RDF reification, and OWL/RDFS axioms other than the three above (`rdfs:subPropertyOf`, `owl:equivalentClass`, …).

Attribute keys stay CURIEs (`ex:sex`), never expanded — pass `strip_attribute_prefixes=true` (or check **Suppress Attribute Prefixes** in the Web UI's Import window) to rewrite them to their local name (`ex:sex` → `sex`, `http://example.org/description` → `description`); a key whose local name would collide with another's is left untouched. Same option works on a native export import too.

Same `create`/`merge` modes, per-item error handling, and 100 MB size limit as a native export import — see the Web UI's [Help](#web-ui) → *Importing RDF (concepts, examples, caveats)* topic for the full worked-example gallery and every documented gotcha (e.g. a quoted numeric-looking string like `"12345"` still becomes a number, not text).

---

## Inferencing

HypergraphAI's inference engine (`hgai/core/inference.py`) derives implicit knowledge from the relationships explicitly stored in the hypergraph, computed live at query time — nothing inferred is ever persisted. Relation semantics (which relations are transitive, symmetric, each other's inverse, or broader/narrower than one another) are never hardcoded: they're declared as ordinary axiom hyperedges asserting a small, fixed control-vocabulary relation between `RelationType` hypernodes — `owl:transitive`, `owl:symmetric`, `owl:inverse-of`, `skos:broaderTransitive`, `skos:narrowerTransitive`. The engine recognizes these control-vocabulary strings; it never knows anything about a specific domain relation, so declaring a new inference rule is a data change (create an axiom hyperedge), not a code change.

Inferencing is opt-in per query — add `infer: true` to an SHQL query (see [SHQL — Semantic Hypergraph Query Language](#shql--semantic-hypergraph-query-language) below). It has no effect unless the query also matches a `relation:` that actually carries one of these axioms in the graph being queried.

### Axiom Expansion (inverse-of / symmetric / superproperty / transitive)

Given the literal hyperedges an SHQL edge pattern already matched, `expand_edge_closure` synthesizes additional derived edges from whatever `owl:inverse-of`, `owl:symmetric`, `skos:broaderTransitive`/`narrowerTransitive`, and `owl:transitive` axiom hyperedges exist for those edges' relations:

- **`owl:inverse-of [R, R']`** — for a hub-flavor edge, each (hub, spoke) pair also implies a 2-member `R'` edge `(spoke, hub)`. E.g. the `hello-world` seed declares `owl:inverse-of [rel:member, rel:member-of]`, so every `rel:member` fact also implies the reverse `rel:member-of` fact.
- **`owl:symmetric`** — every member of a symmetric-flavor edge is mutually equivalent to every other; A related-to B implies B related-to A.
- **`skos:broaderTransitive` / `narrowerTransitive` (superproperty projection)** — if a fact's relation is narrower than one or more broader relations (walked transitively over the axiom graph, so a multi-hop relation hierarchy — e.g. `father` narrower-than `parent` narrower-than `ancestor` — projects through every level), the same fact is copied onto each broader relation unchanged.
- **`owl:transitive`** — unlike the other three, this isn't a per-edge transformation: reachability is a whole-relation, whole-graph property. Once per distinct relation seen in the candidate set (not once per edge), `_expand_transitive_relation` walks the complete network of that relation's literal facts and synthesizes every non-1-hop pair as a 2-member hub edge — e.g. given `rel:parent` facts `A→B→C` and an `owl:transitive` axiom on `rel:parent`, it synthesizes `A→C`. This is what lets a general, open-ended `infer: true` query — including Visualize's whole-graph "show inferred" fetch — surface transitively-derived facts, not just a targeted single-pair reachability question (see [Transitive-Closure Reachability](#transitive-closure-reachability) below for that separate, narrower use case).

This runs to a fixed point (`expand_edge_closure` re-expands its own output — including transitively-derived edges, which may themselves have an inverse or a broader projection — until a round produces nothing new, bounded by `max_iterations`), and dedupes by the individual atomic `(relation, subject, object)` facts each candidate asserts — not by edge shape — so the same fact reached two different ways, or via a cyclic axiom graph, is only returned once. Inferred edges carry `_inferred: true`, `_source_edge` (the literal edge it was derived from — `null` for a transitively-derived edge, which has no single source edge), and `_axiom` (the axiom hyperedge that licensed it); a transitively-derived edge additionally carries `_transitive: true` and `_transitive_path` (the ordered chain of literal hyperedge IDs connecting the pair).

In SHQL, this expansion is spliced into an edge pattern's candidate set *before* member-pattern matching and variable binding run — so an inferred edge is first-class: it can bind `?vars`, anchor a later hop, and chain into a further `where:` pattern exactly like a literal edge. This also means the *literal* candidate fetch itself is relation- and member-agnostic whenever `infer: true` is set (a `relation:`/concrete `members:` filter is applied only *after* expansion) — otherwise a query naming only the *inferred* side of a relation, or a fully-resolved 2-endpoint transitive pattern (neither of which corresponds to a single literal edge), would be starved of anything to expand from.

### Transitive-Closure Reachability

Separately, `check_transitive`/`walk_closure` answer a single targeted reachability *question* over a chain of literal fact edges: is node A transitively connected to node B through a chain of edges of a given relation (or: what's everything reachable from A, or: what's the specific path)? This is a cycle-safe breadth-first walk (`walk_closure`, `max_depth: 10` by default), self-gated on an `owl:transitive` axiom actually existing — nothing fires for a relation nobody declared transitive. It's exposed directly via `POST /graphs/{graph_id}/infer/transitive` (and the equivalent MCP tool) for a one-off answer without composing a query, independent of the general SHQL expansion above.

### Edge Flavors

Hyperedge `flavor` describes how one hyperedge's member list decomposes into individual (subject, object) facts — it is unrelated to transitivity, which is a *relation-level* property declared via an `owl:transitive` axiom, not a per-edge setting:

| Flavor | Semantics |
|---|---|
| `hub` | The first member (lowest `seq`) is the hub; every other member is an independent (hub, spoke) fact — e.g. "adam is father of cain/abel/seth" is 3 separate facts, not one N-ary fact |
| `symmetric` | Every member is mutually equivalent to every other — e.g. `sibling(moe, larry, curly)` implies all 6 directed pairs |

### Roadmap

Shipped: axiom-driven inverse-of/symmetric/superproperty/transitive expansion, SKOS `broader`/`narrower` projection, and single-pair transitive-closure reachability, all wired into SHQL behind `infer: true`. Planned for future releases:

- **Rule-based inferencing** — user-defined inference rules stored as hypernodes of type `InferenceRule`, evaluated at query time
- **Cross-graph inferencing** — axiom expansion and transitive walks spanning multiple hypergraphs in a logical composition or mesh
- **Materialized inference cache** — optional pre-computation of common transitive closures, stored in `query_cache` and invalidated on edge mutations
- **OWL-lite property chains** — support for `owl:propertyChainAxiom`-style inference, where a chain of relations implies a derived relation

---

## SHQL — Semantic Hypergraph Query Language

SHQL (pronounced *"shekel"*) is HypergraphAI's query language, implemented as a pluggable module (`hgai_module_shql`). It's a **pattern-matching** language inspired by SPARQL — `?variable` bindings, implicit joins across shared variables, multi-hop traversal, OPTIONAL/UNION, point-in-time queries, aggregation, and axiom-driven inferencing, all over YAML `node`/`edge` patterns.

### Endpoints

```
POST /api/v1/shql/query      Execute an SHQL query
POST /api/v1/shql/validate   Validate an SHQL query (dry run)
```

### Mesh SHQL

All servers in a mesh are queried **concurrently** — total latency equals the slowest server, not the sum of all servers. Unreachable servers are skipped and reported in the `errors` field of the response.

```yaml
shql:
  from: alpha-bravo-mesh
  where:
  - node: ?person
    node_type: Person
  select:
    - ?person.id
    - ?person.label
    - ?person.node_type
    - ?person.attributes
    - ?person.tags
```

Returns all hyperedge group + members. `seq: 0` here isn't just decorative —
it requires the already-bound `?group` to specifically be the hub-flavor
edge's *first* member, not merely one of its members:

```yaml
shql:
  from: alpha-bravo-mesh
  where:
    - node: ?group
      node_type: Group
    - edge: ?hub
      relation: rel:member
      flavor: hub
      members:
        - node_id: ?group
          seq: 0
  select:
    - ?group.id
    - ?group.label
    - ?hub.id
    - ?hub.relation
    - ?hub.members
```

### Dot-Notation Mesh References

Like Mesh SHQL above, all servers are queried **concurrently** — dot-notation refs fan out within the same `asyncio.gather` call.

#### Dot-notation `from:` reference formats

| Format | Meaning |
|--------|---------|
| `mesh.server.graph` | Unowned graph on a specific server |
| `mesh.server.space.graph` | Space-scoped graph on a specific server |
| `mesh.*.graph` | Unowned graph on all servers in the mesh |
| `mesh.*.space.graph` | Space-scoped graph on all servers in the mesh |
| `mesh.server.*` | All unowned graphs on a specific server |

Dots are prohibited in all ID fields, so splitting on `.` is unambiguous. The third component is the space ID for 4-part refs or the graph ID for 3-part refs.

**Local graph notation in SHQL's `from:`:**

| Format | Meaning |
|--------|---------|
| `graph_id` | Unowned local graph (`space_id` is null) |
| `space_id/graph_id` | Space-scoped local graph (slash separator) |

The slash separator is used for local space refs; dots remain reserved for mesh routing only.

```yaml
shql:
  from: alpha-bravo-mesh
  where:
    - node:
        bind: ?n
        node_type: Person
  select:
    - ?n.id
    - ?n.label
    - ?n.type
    - ?n.attributes
    - ?n.tags
  limit: 500
```

### Language Structure

```yaml
shql:
  from: <graph-id>              # required — graph ID or list of IDs
  at: <iso-datetime>            # optional — point-in-time filter
  select:                       # fields to return
    - ?var                      # whole bound entity
    - ?var.label                # single field from bound entity
    - ?var.attributes.city      # nested attribute path
    - "*"                       # everything (default)
  where:                        # ordered list of patterns
    - node:  { ... }            # hypernode pattern
    - edge:  { ... }            # hyperedge pattern
    - filter: "<expression>"    # expression filter
    - optional: [ ... ]         # left outer join — patterns that may not match
    - union:                    # set union of alternative branches
        - patterns: [ ... ]
        - patterns: [ ... ]
  order_by: ?var.field          # optional sort key(s) — a single field, or a list for
                                 # multi-key sort (primary field first); each field may
                                 # carry a trailing " asc"/" desc" (case-insensitive,
                                 # default asc) — e.g. "?e.relation desc", or
                                 # [?e.relation desc, ?e.label] to sort by relation
                                 # descending, then label ascending, within each group
  limit: 100                    # default 500
  offset: 0
  distinct: true                # deduplicate result rows
  infer: true                   # opt-in axiom expansion + transitive closure (see Inferencing)
  aggregate:                    # computed over the full matched/deduplicated result, pre-pagination
    count: true                 # -> meta.count: total matched rows
    group_by: var.field         # -> meta.groups: { "<value>": <count>, ... } — name the *projected row key*
                                 # a matching `select:` entry produces (no leading "?", e.g. `?e.relation` in
                                 # select: becomes row key "e.relation" here)
  as: result_alias
```

### Variables

Variables start with `?` and bind matched entities across patterns. A variable used in two different patterns acts as an implicit join: all patterns sharing `?person` must agree on the same node.

### Node Pattern

```yaml
- node:
    bind: ?var          # bind matched node to this variable
    id: my-node-id      # match by exact id (literal or ?var)
    type: Person        # match by node type
    tags: [stooge]      # must have all listed tags
    status: active      # default: active
    attributes:
      rat_pack_member: true         # exact attribute match
      # born: { $lt: "1910-01-01" } # MongoDB operators work here too
```

### Edge Pattern

```yaml
- edge:
    bind: ?edge         # bind matched edge to this variable
    id: edge:classic-stooges   # match by exact edge id (literal or ?var)
    relation: rel:member
    flavor: hub
    tags: [some-tag]
    attributes:
      some_key: some-value
    members:            # member patterns (order-independent)
      - node:
          bind: ?group
          id: group:three-stooges
      - node:
          bind: ?other              # bind any other member
```

A member pattern matches on `id`/`node_id`, `seq` and `bind` only — a `type`, `tags` or `attributes` inside it is ignored. To constrain a member's own properties, bind its id (`node_id: ?member_id`) and join to a `node:` pattern (`id: ?member_id`, `type: Person`); see the worked examples below. Write patterns in block style: an unquoted `?variable` inside flow-style `{ ... }` or `[ ... ]` is not valid YAML.

### Filter Expressions

FILTER expressions are strings supporting:

| Syntax | Description |
|---|---|
| `?var.field = value` | Equality |
| `?var.field != value` | Inequality |
| `?var.field < 10` | Comparison (`<`, `>`, `<=`, `>=`) |
| `?var.field IN [a, b, c]` | Membership |
| `CONTAINS(?var.label, "text")` | Case-insensitive substring |
| `STARTS_WITH(?var.label, "Mo")` | Prefix match |
| `ENDS_WITH(?var.label, "ard")` | Suffix match |
| `BOUND(?var)` | Variable is bound |
| `IS_TYPE(?var, "Person")` | Type check |
| `expr AND expr` | Logical AND |
| `expr OR expr` | Logical OR |
| `NOT expr` | Logical NOT |

---

### Examples

All examples use the seed hypergraphs shipped in `scripts/seeds/` — `hello-world` (Three Stooges, Rat Pack and Beatles lineups) and `eden` (a small family tree). Load them with `python scripts/seed_data.py`, then paste any query into the Web UI's **Query (SHQL)** screen; each one runs as written.

> **Member patterns match by id and position only.** Inside an edge's `members:` a pattern matches on `node_id` (or `id`), `seq`, and `bind`. To also constrain a member's own properties (`type`, `tags`, `attributes`), bind its id to a variable and join to a `node:` pattern on that id, as in examples 3, 6, 7 and 18.

#### 1. Find all Person hypernodes

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
    - ?person.description
  where:
    - node:
        bind: ?person
        type: Person
  order_by: ?person.label
```

#### 2. Find which hyperedges contain a specific node (Moe)

```yaml
shql:
  from: hello-world
  select:
    - ?edge.id
    - ?edge.label
    - ?edge.relation
  where:
    - edge:
        bind: ?edge
        members:
          - node:
              id: person:moe
```

#### 3. Multi-hop join — the members of every Three Stooges lineup

A member pattern matches on `node_id` and `seq` only — it binds the member's *id*. To also constrain the member's own properties (its `type`, `tags`, `attributes`), bind the id to a variable and join to a `node` pattern on that id. The shared `?person_id` is the join key:

```yaml
shql:
  from: hello-world
  select:
    - ?edge.label
    - ?stooge.label
  where:
    - edge:
        bind: ?edge
        relation: rel:member
        members:
          - node_id: group:three-stooges
          - node_id: ?person_id
    - node:
        bind: ?stooge
        id: ?person_id
        type: Person
  order_by:
    - ?edge.label
    - ?stooge.label
```

#### 4. FILTER on a property

Match `description` text with a filter expression (see [Filter Expressions](#filter-expressions)). Node attributes can also be matched directly inside the pattern — here only Frank Sinatra has `rat_pack_member: true`:

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
    - ?person.description
  where:
    - node:
        bind: ?person
        type: Person
    - filter: "CONTAINS(?person.description, 'Howard')"
```

#### 4b. Match node attributes in the pattern

```yaml
shql:
  from: hello-world
  select:
    - ?person.label
    - ?person.attributes
  where:
    - node:
        bind: ?person
        type: Person
        attributes:
          rat_pack_member: true
```

#### 5. OPTIONAL — include the Howard-brothers edge where it exists

```yaml
shql:
  from: hello-world
  select:
    - ?person.label
    - ?brothers.label
  where:
    - node:
        bind: ?person
        type: Person
    - optional:
        - edge:
            bind: ?brothers
            relation: family:brother
            members:
              - node:
                  bind: ?person
```

#### 6. UNION — members of the Beatles OR the Rat Pack

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
  where:
    - union:
        - patterns:
            - edge:
                relation: rel:member
                members:
                  - node_id: group:beatles
                  - node_id: ?member_id
        - patterns:
            - edge:
                relation: rel:member
                members:
                  - node_id: group:rat-pack
                  - node_id: ?member_id
    - node:
        bind: ?person
        id: ?member_id
        type: Person
  distinct: true
  order_by: ?person.label
```

#### 7. Point-in-time query — who was a Stooge in 1940?

```yaml
shql:
  from: hello-world
  at: "1940-06-01T00:00:00Z"
  select:
    - ?stooge.label
    - ?edge.label
  where:
    - edge:
        bind: ?edge
        relation: rel:member
        members:
          - node_id: group:three-stooges
          - node_id: ?person_id
    - node:
        bind: ?stooge
        id: ?person_id
        type: Person
```

### Space-scoped Graph References

Space-scoped graphs use the slash-separator syntax: `space_id/graph_id`. Unowned graphs are referenced by bare `graph_id`.

| `from:` value | Meaning |
|---|---|
| `my-graph` | Unowned local graph (`space_id` is null) |
| `alpha/alpha-hg` | Graph `alpha-hg` scoped to space `alpha` |

#### 8. Find all nodes in a space-scoped graph

```yaml
shql:
  from: alpha/alpha-hg
  select:
    - ?person.id
    - ?person.label
    - ?person.attributes
  where:
    - node:
        bind: ?person
        type: Person
  order_by: ?person.label
  as: space_people
```

#### 9. Multi-hop join across a space-scoped graph

```yaml
shql:
  from: alpha/alpha-hg
  select:
    - ?person.label
    - ?membership.id
    - ?membership.relation
  where:
    - node:
        bind: ?person
        type: Person
    - edge:
        bind: ?membership
        relation: rel:member
        members:
          - node:
              bind: ?person
  as: space_memberships
```

#### 10. Multi-graph query across two spaces

```yaml
shql:
  from:
    - alpha/alpha-hg
    - beta/beta-hg
  select:
    - ?n.id
    - ?n.label
    - ?n.type
  where:
    - node:
        bind: ?n
        type: Person
  order_by: ?n.label
  as: cross_space_people
```

#### 11. Mix a space-scoped graph with an unowned global graph

```yaml
shql:
  from:
    - hello-world
    - alpha/alpha-hg
  select:
    - ?n.id
    - ?n.label
    - ?n.type
  where:
    - node:
        bind: ?n
  as: global_and_space
```

#### 12. Point-in-time query on a space-scoped graph

```yaml
shql:
  from: alpha/alpha-hg
  at: "1940-06-01T00:00:00Z"
  select:
    - ?stooge.label
    - ?edge.label
  where:
    - edge:
        bind: ?edge
        relation: rel:member
        members:
          - node_id: group:three-stooges
          - node_id: ?person_id
    - node:
        bind: ?stooge
        id: ?person_id
        type: Person
  as: space_stooges_in_1940
```

For remote graphs on a mesh server, use the 4-component dot-notation `mesh.server.space.graph`:

```yaml
shql:
  from: my-mesh.remote-server.alpha.alpha-hg
  select:
    - ?n.id
    - ?n.label
    - ?n._mesh_server_id
  where:
    - node:
        bind: ?n
        type: Person
  as: remote_space_people
```

#### 13. Positional member filter — find the first member by seq

Combine `seq` with `node_id` inside the same member pattern to require both to hold on the **same** array element, rather than "contains this node anywhere." The query below only matches `rel:lineup` edges whose *first* member (`seq: 0`) is `group:three-stooges` (the lineups edge, which also lists other edges as members):

```yaml
shql:
  from: hello-world
  select:
    - ?edge.id
    - ?edge.label
    - ?edge.members
  where:
    - edge:
        bind: ?edge
        relation: rel:lineup
        members:
          - node_id: group:three-stooges
            seq: 0
```

#### 14. Aggregate — count edges grouped by relation

`aggregate` is computed over the full matched, deduplicated result set, before `order_by`/`limit`/`offset` paginate it. `group_by` names the *projected row key* a `select:` entry produces (no leading `?`) — here `?edge.relation` in `select:` becomes the row key `edge.relation`:

```yaml
shql:
  from: hello-world
  select:
    - ?edge.relation
  where:
    - edge:
        bind: ?edge
  aggregate:
    count: true
    group_by: edge.relation
```

#### 15. Inferencing — axiom-driven expansion

`infer: true` extends the live candidate set with synthesized edges before member-pattern matching runs. The `hello-world` seed declares an `owl:inverse-of` axiom between `rel:member` and `rel:member-of`, so this query returns `rel:member-of` edges (the reverse of each literal `rel:member` fact) tagged `_inferred: true`, though none is stored:

```yaml
shql:
  from: hello-world
  infer: true
  select:
    - ?edge.relation
    - ?edge.members
    - ?edge._inferred
    - ?edge._axiom
  where:
    - edge:
        bind: ?edge
        relation: rel:member-of
```

#### 16. Multi-key sort with descending order

`order_by` takes a list to sort by more than one field, and each field may carry a trailing `asc`/`desc` (default `asc`) — independent per field:

```yaml
shql:
  from: hello-world
  select:
    - ?edge.relation
    - ?edge.label
  where:
    - edge:
        bind: ?edge
  order_by:
    - ?edge.relation desc
    - ?edge.label
```

#### 17. Eden — who are the parents of Cain?

The `eden` seed is a small family tree. A `rel:parent` edge is a hub edge: the child is the hub (`seq: 0`) and the parents follow.

```yaml
shql:
  from: eden
  select:
    - ?parent.label
  where:
    - edge:
        relation: rel:parent
        members:
          - node_id: person:cain
            seq: 0
          - node_id: ?parent_id
    - node:
        bind: ?parent
        id: ?parent_id
```

#### 18. Eden — who is the mother of Cain?

Join to the parent's node and test its `sex` attribute:

```yaml
shql:
  from: eden
  select:
    - ?mother.label
  where:
    - edge:
        relation: rel:parent
        members:
          - node_id: person:cain
            seq: 0
          - node_id: ?parent_id
    - node:
        bind: ?mother
        id: ?parent_id
        attributes:
          sex: female
```

#### 19. Eden — inferred: who is Enoch's parent?

Only Seth's `rel:child` edge (Seth → Enosh, Enoch) is stored. With `infer: true` the `owl:inverse-of` axiom between `rel:child` and `rel:parent` derives the reverse fact, so Enoch's parent is found:

```yaml
shql:
  from: eden
  infer: true
  select:
    - ?ancestor.label
  where:
    - edge:
        relation: rel:parent
        members:
          - node_id: person:enoch
            seq: 0
          - node_id: ?ancestor_id
    - node:
        bind: ?ancestor
        id: ?ancestor_id
  distinct: true
```

### Module Location

```
hgai_module_shql/
├── __init__.py       module export
├── module.py         SHQLModule class (router registration)
├── parser.py         parse_shql() + validate_shql()
├── engine.py         execute_shql() — binding sets, pattern evaluation, projection
└── api_router.py     POST /api/v1/shql/query and /validate
```

---

## Module Development

See [docs/module-development.md](docs/module-development.md) for the full guide.

Modules follow the naming convention: `hgai_module_<name>/`

Minimum module structure:
```
hgai_module_mymodule/
├── __init__.py        # exports MyModule
├── module.py          # MyModule class with get_router() or get_app()
└── api_router.py      # FastAPI router (optional)
```

Modules are mounted conditionally in `hgai/main.py` — a missing or broken module logs a warning and is skipped; the server continues normally.

---

## Administration

### Default Admin Account
- Username: `admin`
- Password: `pwd357`
- **Change this password immediately after first login.**

### RBAC Roles
| Role | Description |
|------|-------------|
| `admin` | Full system access including account management |
| `user` | Read/write access to permitted hypergraphs |
| `agent` | API/MCP-only access for AI agents |
| `readonly` | Read-only access |

### Spaces (Multi-Tenant Namespaces)

**Spaces** group hypergraphs for multi-tenant deployments. Each space has members with roles:

| Space Role | Permitted Operations |
|------------|---------------------|
| `owner` | read, write, delete, admin, query, export, import + manage space |
| `admin` | read, write, delete, query, export, import + manage members |
| `member` | read, write, query, export, import |
| `viewer` | read, query, export |

#### Access Control Model

Space membership is the **sole gate** for space-scoped graphs. `permissions.graphs` wildcards (e.g. `["*"]`) do **not** grant access to graphs in a space the account is not a member of. Access is resolved in this exact order:

1. **Global admin** — accounts with `"admin"` in `roles` bypass all checks.
2. **Space membership** — when the graph belongs to a space, the account must be a member of that space. Non-members are rejected regardless of `permissions.graphs`.
3. **`permissions.graphs`** — applies only to unowned (non-space) graphs.

This ensures that a `["*"]` permissions wildcard cannot leak across tenant boundaries.

The same resolution applies on every surface — REST, the SHQL query endpoint (`POST /shql/query`, which needs the `query` operation on each `from:` graph and returns `403` otherwise) and the MCP tools. Federated mesh queries (mesh ids and dot-notation refs in `from:`, and the `hgai_mesh_*` tools) are admin-only.

#### Space Membership Management

Members can be managed from the **space perspective** (via the space itself) or the **account perspective** (admin shortcut routes on the account):

```bash
# From the space: add alice as a member
curl -X POST http://localhost:8000/api/v1/spaces/my-team/members/alice \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "member"}'

# From the account: assign alice to a space (admin only)
curl -X POST http://localhost:8000/api/v1/accounts/alice/spaces/my-team \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "member"}'

# List all spaces alice belongs to (admin only)
curl http://localhost:8000/api/v1/accounts/alice/spaces \
  -H "Authorization: Bearer <token>"

# Remove alice from a space (admin only)
curl -X DELETE http://localhost:8000/api/v1/accounts/alice/spaces/my-team \
  -H "Authorization: Bearer <token>"
```

When an account is deleted, it is automatically removed from all space `members` arrays.

#### Space Membership in the Admin UI

In the **Accounts** admin screen, editing any account shows a **Space Memberships** tab listing every space the user belongs to. From this tab, an admin can:
- Change a member's role using an inline dropdown
- Remove a member from a space
- Assign the account to a new space (with role selection)

Because graph uniqueness is enforced per-space, `team-a` and `team-b` can each have a graph named `my-graph` with no conflict. Flat `/graphs/*` routes address only unowned graphs (`space_id` is null). Space-owned graphs are addressed via `/spaces/{space_id}/graphs/{graph_id}`.

```bash
# Create a space
curl -X POST http://localhost:8000/api/v1/spaces \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"id": "my-team", "label": "My Team"}'

# Add a member
curl -X POST http://localhost:8000/api/v1/spaces/my-team/members \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "role": "member"}'

# Create a graph inside the space (same ID can exist in other spaces)
curl -X POST http://localhost:8000/api/v1/spaces/my-team/graphs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"id": "my-graph", "label": "My Graph"}'

# Get a space-scoped graph
curl http://localhost:8000/api/v1/spaces/my-team/graphs/my-graph \
  -H "Authorization: Bearer <token>"

# Full node/edge CRUD under a space
curl http://localhost:8000/api/v1/spaces/my-team/graphs/my-graph/nodes \
  -H "Authorization: Bearer <token>"
```

**SHQL `from:` for space-scoped graphs** use slash notation:

```yaml
shql:
  from: my-team/my-graph       # space-scoped
  where:
    - edge:
        bind: ?e
```

```yaml
shql:
  from:
    - my-team/my-graph         # space-scoped
    - other-team/my-graph      # same graph ID, different space
    - unowned-graph            # unowned (no space)
```

**Mesh dot-notation for space-scoped remote graphs** uses 4 components:

```yaml
shql:
  from: alpha-bravo-mesh.server-a.my-team.my-graph
```

MCP tools for spaces: `hgai_space_list`, `hgai_space_get`, `hgai_space_create`, `hgai_space_add_member`, `hgai_space_list_graphs`.

### Backup
```bash
# Backup MongoDB
docker-compose exec mongo mongodump \
  --username admin --password pwd357 \
  --authenticationDatabase admin \
  --db hgai --out /backup

# Restore
docker-compose exec mongo mongorestore \
  --username admin --password pwd357 \
  --authenticationDatabase admin \
  --db hgai /backup/hgai
```

### MongoDB Indexes

Indexes are created automatically at server startup via `ensure_indexes()` in `hgai_module_storage_mongodb/indexes.py`, called during `StorageBackend.ensure_schema()`. The call is idempotent — MongoDB skips indexes that already exist with the same name and definition.

#### hypergraphs

| Index | Fields | Options | Purpose |
|-------|--------|---------|---------|
| `id_unique` | `id` | unique | Graph lookup by ID (every request) |
| `status` | `status` | — | Graph list and active-graph queries |

#### hypernodes

| Index | Fields | Options | Purpose |
|-------|--------|---------|---------|
| `id_graph_unique` | `id, hypergraph_id` | unique | Single-node lookup; enforces ID uniqueness per graph |
| `graph_status` | `hypergraph_id, status` | — | Hot path — used on every node list query |
| `graph_type` | `hypergraph_id, type` | — | `node_type` filter in SHQL |
| `tags` | `tags` | multikey | Tag `$all` filter |
| `label` | `label` | — | Label regex/text search |
| `graph_pit` | `hypergraph_id, valid_from, valid_to` | sparse | Point-in-time queries |

#### hyperedges

| Index | Fields | Options | Purpose |
|-------|--------|---------|---------|
| `id_graph_unique` | `id, hypergraph_id` | unique | Edge lookup by ID |
| `hyperkey_graph_unique` | `hyperkey, hypergraph_id` | unique | Hyperkey lookup; enforces semantic deduplication at DB level |
| `graph_status` | `hypergraph_id, status` | — | Hot path — used on every edge list query |
| `graph_relation` | `hypergraph_id, relation` | — | Relation filter in SHQL |
| `members_node_id` | `members.node_id` | multikey | Node membership queries (`node_id` filter) |
| `graph_pit` | `hypergraph_id, valid_from, valid_to` | sparse | Point-in-time queries |

#### meshes

| Index | Fields | Options | Purpose |
|-------|--------|---------|---------|
| `id_unique` | `id` | unique | Mesh lookup by ID |

#### accounts

| Index | Fields | Options | Purpose |
|-------|--------|---------|---------|
| `username_unique` | `username` | unique | Authentication lookups; enforces unique usernames |

#### query_cache

| Index | Fields | Options | Purpose |
|-------|--------|---------|---------|
| `cache_key_unique` | `cache_key` | unique | Fast cache hit/miss lookups |
| `graph_ids` | `graph_ids` | multikey | Graph-scoped invalidation — `delete_many({"graph_ids": id})` |
| `expires_at_ttl` | `expires_at` | TTL `expireAfterSeconds=0` | MongoDB background reaper auto-deletes expired entries |

The TTL index on `expires_at` means MongoDB's background thread removes expired cache documents automatically — no manual cleanup required. The manual TTL check in `cache.py` remains as a belt-and-suspenders fallback for immediate consistency on reads.

The `graph_ids` multikey index enables graph-scoped cache invalidation: every cache document stores the list of local graph IDs it queried, so a write to graph `X` only evicts entries that touched `X`. See [Graph-scoped cache invalidation](#graph-scoped-cache-invalidation).

#### audit_log

| Index | Fields | Options | Purpose |
|-------|--------|---------|---------|
| `timestamp_desc` | `timestamp` (desc) | — | Time-ordered audit log reads |

#### Verifying indexes in MongoDB

```bash
# Connect to the running MongoDB instance
mongosh --username admin --password pwd357 --authenticationDatabase admin

# List indexes on a collection
use hgai
db.hypernodes.getIndexes()
db.hyperedges.getIndexes()
db.query_cache.getIndexes()
```

### Performance

#### Concurrent mesh fan-out

All mesh fan-out operations use `asyncio.gather` so server calls run in parallel rather than sequentially. This affects:

| Function | Before | After |
|---|---|---|
| `ping_mesh` | N servers × 10 s timeout | ~10 s regardless of N |
| `sync_mesh_graphs` | N servers × fetch time | ~1× fetch time |
| `federated_shql` | N servers × query time | ~1× query time |
| `execute_dot_refs` | N servers × query time | ~1× query time |
| `resolve_dot_refs` | Sequential mesh + graph lookups | Concurrent mesh lookups + concurrent graph fetches |

Within each function the pattern is:

1. **Graph resolution** — `asyncio.gather(*[_graphs_for_server(s) for s in servers])` fetches cached or live graph lists from all servers at once.
2. **Query execution** — `asyncio.gather(*[_query_server(s, ...) for s in active], return_exceptions=True)` dispatches queries concurrently; `return_exceptions=True` means a single unreachable server does not cancel the others.
3. **Result merge** — items from all servers are collected and returned in the response; failures appear in the `errors` list.

The local server is always handled by a direct engine call (no HTTP), so it adds near-zero latency regardless of which mesh it is registered under.

#### Graph-scoped cache invalidation

Every cached query result stores the list of local hypergraph IDs it queried:

```json
{
  "cache_key": "abc123...",
  "graph_ids": ["stooges-graph", "classics-graph"],
  "result": { ... },
  "expires_at": "2026-04-06T12:00:00Z"
}
```

When a hypernode or hyperedge in graph `stooges-graph` is written (create, update, delete), `invalidate_cache("stooges-graph")` runs `delete_many({"graph_ids": "stooges-graph"})` — removing only entries that queried that graph. Cached results for `classics-graph` and all other graphs remain intact.

A full flush (no argument) still runs `delete_many({})` and is used when a hypergraph itself is created, updated, or deleted.

**Scope of `graph_ids` per cache entry:**

| Query type | `graph_ids` stored | Invalidation behaviour |
|---|---|---|
| Local query (`from: my-graph`) | `["my-graph"]` | Evicted when `my-graph` is mutated |
| Multi-graph (`from: [a, b]`) | `["a", "b"]` | Evicted when either `a` or `b` is mutated |
| Dot-notation remote ref | `[]` (no local graphs) | Never evicted by graph mutation; expires via TTL |
| Dot-notation with local ref | `["local-graph"]` | Evicted when `local-graph` is mutated |
| Logical graph expansion | Resolved physical IDs | Evicted when any composed graph is mutated |

Dot-notation refs that point to fully remote graphs cannot be graph-scoped (the local server has no visibility into remote mutations), so those entries expire naturally via the TTL index.

#### Shared HTTP client

All outbound mesh HTTP calls use a single `httpx.AsyncClient` instance defined in `hgai_module_mesh/engine.py` rather than creating and tearing down a new client per request.

```
Before: each call → new TCP handshake → TLS negotiation → request → close connection
After:  each call → reuse pooled connection → request  (TCP/TLS cost paid once)
```

**Connection pool settings** (configurable in `engine.py`):

| Parameter | Value | Meaning |
|---|---|---|
| `max_connections` | 100 | Total concurrent connections across all mesh servers |
| `max_keepalive_connections` | 20 | Idle keep-alive connections held open for reuse |
| `keepalive_expiry` | 30 s | How long an idle connection is kept before closing |
| `timeout` | 10 s | Per-request timeout (connect + read) |

**Lifecycle** — the client is created lazily on first use by `get_http_client()`, and explicitly closed at application shutdown by `close_http_client()` which is called from the FastAPI lifespan in `hgai/main.py`. If the mesh module is not installed, the shutdown hook is skipped silently.

**Thread safety** — `httpx.AsyncClient` is safe to share across concurrent coroutines. With `asyncio.gather` fan-out, multiple server queries share the same client and its connection pool simultaneously.

#### MongoDB indexes

See [MongoDB Indexes](#mongodb-indexes) above. Indexes are the single highest-impact change for query latency — without them every query performs a full collection scan regardless of concurrent fan-out.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

HypergraphAI core engine and modules are open-source under the MIT License.
Custom or advanced modules may have different licensing as determined by their authors.
