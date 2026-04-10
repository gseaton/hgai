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
- `relation` — semantic relation type (e.g., `has-member`, `sibling`, `broader`)
- `members` — ordered list of participating hypernodes with optional roles
- `flavor` — relationship pattern: `hub`, `symmetric`, `direct`, `transitive`, `inverse-transitive`
- `attributes` — arbitrary JSON document
- `hyperkey` — SHA-256 hash ID generated from the normalized edge structure

### Hypergraph
A **hypergraph** is a named container for hypernodes and hyperedges. Hypergraphs can be:
- **Instantiated** — physical collections in MongoDB
- **Logical** — virtual compositions of one or more other hypergraphs (local or remote)

### HQL (Hypergraph Query Language)
HypergraphAI queries are written in YAML format:

```yaml
hql:
  from: my-graph
  match:
    type: hyperedge
    relation: has-member
  where:
    tags:
      - original
  return:
    - members
    - attributes
  as: result
```

### WHERE Operators

┌───────────────────────┬───────────────────┐
│       Operator        │       YAML        │
├───────────────────────┼───────────────────┤
│ less than             │ $lt: 20           │
├───────────────────────┼───────────────────┤
│ less than or equal    │ $lte: 20          │
├───────────────────────┼───────────────────┤
│ greater than          │ $gt: 20           │
├───────────────────────┼───────────────────┤
│ greater than or equal │ $gte: 20          │
├───────────────────────┼───────────────────┤
│ not equal             │ $ne: 20           │
├───────────────────────┼───────────────────┤
│ in a list             │ $in: [10, 15, 20] │
└───────────────────────┴───────────────────┘

### WHERE Boolean Operators

#### Boolean Operators
- `$or`
- `$and`
- `$nor`
- `$not`

#### Example WHERE Boolean Query

```yaml
hql:                                                                                                                                              
    from: my-graph                                                                                                                                
    match:                                                                                                                                          
      type: any
    where:                                                                                                                                          
      $or:                                                                                                                                        
        - attributes.answer:
            $lt: 10
        - attributes.answer:
            $gt: 99                                                                                                                                 
    return:
      - id                                                                                                                                          
      - label                                               
      - type
      - attributes
    as: answer_out_of_range
```

The `$or` key passes directly through to MongoDB unchanged — the query engine maps any unrecognized `where` key straight 
to the MongoDB query document, so all standard MongoDB logical operators work: `$or`, `$and`, `$nor`, `$not`.

### Query Examples

Multi-graph composition:
```yaml
hql:
  from:
    - graph-1
    - graph-2
  match:
    type: hypernode
    node_type: Person
  where:
    attributes.city: Paris
  return:
    - id
    - label
    - attributes
```

Point-in-time query:
```yaml
hql:
  from: presidents
  at: "1963-11-22T00:00:00Z"
  match:
    type: hyperedge
    relation: rel:holds-office
  return:
    - members
```

```yaml
hql:
    from: 
      - hg-alpha
      - hg-bravo
    at: "1944-11-22T00:00:00Z"
    match:
      type: hyperedge
    where:
      relation: rel:president-of
      flavor: hub
      members.node_id:
        $all: [nation:usa]
      members.seq: 0
    return:
      - id
      - relation
      - members
      - attributes
    as: potus-at
```

The SHQL needs to: (1) find the president-of edge that includes nation:usa as a member, (2) bind the other member (seq 0) as the president's node ID, then (3) join to the Person node to project the requested fields.

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

┌──────┬──────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────┐
│ Step │                 Pattern                  │                                      Effect                                       │
├──────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
│ 1    │ edge: ?potus_edge with nation:usa member │ Finds edges where nation:usa is a member, binding the edge doc to ?potus_edge     │
├──────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
│ 2    │ node_id: ?president_id + seq: 0          │ Binds the seq-0 member's node ID to ?president_id                                 │
├──────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
│ 3    │ node: ?president + id: ?president_id     │ Resolves ?president_id → MongoDB query, binding the full Person doc to ?president │
├──────┼──────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
│ 4    │ select                                   │ Projects id, label, description, attributes from the bound Person                 │
└──────┴──────────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────┘

The `at:` timestamp is respected at every stage — both the edge lookup and node lookup are evaluated at the point-in-time `1948-11-22`, so the result reflects whoever held the office on that date. 

---

Attributes Query:

```yaml
hql:
    from: hello-world
    match:
      type: any
    where:
      attributes.family: Horwitz
    return:
      - id
      - label
      - attributes
      - _entity_type
    as: horwitz_family
```
Matches any hypernode or hyperedge whose attributes.family == "Horwitz" — 
in the seed data this returns the Horwitz Brothers sibling edge.

Numeric WHERE Operators:

```yaml
hql:
  from: 
    - hg-alpha
    - hg-bravo
  match:
    type: any
  where:
    attributes.answer:
      $gt: 2
  return:
    - id
    - label
    - type
    - attributes
  as: answer_lt_20
```

Hyperedges with member node/edge ids:

```yaml
hql:
    from: hg-alpha
    match:
      type: hyperedge
    where:
      members:
        node_id: person:curly-joe
    return:
      - id
      - relation
      - members
      - attributes
    as: edges_containing_moe
```
The `members.node_id` path is handled as a special case in the HQL engine, translating to a MongoDB `members.node_id` field match — which works against the array of `member` objects regardless of position.

To match edges containing any one of several nodes:

```yaml
where:
  members:
    node_id:
      $in: [moe-howard, larry-fine]
```

To match edges containing all of a set of nodes:

```yaml
hql:
    from: hg-alpha
    match:
      type: hyperedge
    where:
    members.node_id:
      $all: [person:moe, person:larry]
    return:
      - id
      - relation
      - members
      - attributes
    as: edges_containing_moe_et
```

### Space-scoped Graph References

Graphs owned by a space are referenced with a slash separator: `space_id/graph_id`. This distinguishes space-scoped graphs from unowned graphs and from mesh dot-notation refs.

| `from:` value | Meaning |
|---|---|
| `my-graph` | Unowned local graph (`space_id` is null) |
| `alpha/alpha-hg` | Graph `alpha-hg` scoped to space `alpha` |

Query all nodes in a space-scoped graph:

```yaml
hql:
  from: alpha/alpha-hg
  match:
    type: hypernode
  return:
    - id
    - label
    - type
    - attributes
```

Query edges by relation in a space-scoped graph:

```yaml
hql:
  from: alpha/alpha-hg
  match:
    type: hyperedge
    relation: has-member
  return:
    - id
    - relation
    - members
    - attributes
```

Multi-graph query across two spaces:

```yaml
hql:
  from:
    - alpha/alpha-hg
    - beta/beta-hg
  match:
    type: hypernode
    node_type: Person
  return:
    - id
    - label
    - attributes
```

Mix a space-scoped graph with an unowned global graph:

```yaml
hql:
  from:
    - hello-world
    - alpha/alpha-hg
  match:
    type: hypernode
  return:
    - id
    - label
    - type
```

Point-in-time query on a space-scoped graph:

```yaml
hql:
  from: alpha/alpha-hg
  at: "1940-06-01T00:00:00Z"
  match:
    type: hyperedge
    relation: has-member
  return:
    - members
    - attributes
    - valid_from
    - valid_to
```

For remote graphs on a mesh server, use the 4-component dot-notation `mesh.server.space.graph`:

```yaml
hql:
  from: my-mesh.remote-server.alpha.alpha-hg
  match:
    type: hypernode
  return:
    - id
    - label
    - _mesh_server_id
```

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
├── hgai_module_hql/             # HQL — Hypergraph Query Language module
│   ├── engine.py                # HQL parser + executor (YAML, PIT, multi-graph, aggregation)
│   └── api_router.py            # POST /api/v1/query, /validate, /cache/invalidate
│
├── hgai_module_shql/            # SHQL — Semantic Hypergraph Query Language module
│   ├── parser.py                # parse_shql() + validate_shql()
│   ├── engine.py                # execute_shql() — binding sets, pattern evaluation, projection
│   └── api_router.py            # POST /api/v1/shql/query, /validate
│
├── hgai_module_mesh/            # Mesh — distributed server registry + federation module
│   ├── models.py                # MeshServer, MeshCreate, MeshUpdate, MeshResponse
│   ├── engine.py                # ping, sync, federated HQL
│   └── api_router.py            # CRUD + /ping, /sync, /query endpoints
│
├── hgai_module_mcp/             # MCP — Model Context Protocol module
│   └── server.py                # FastMCP server: 14 tools (CRUD + HQL/SHQL query)
│
├── ui/                          # Web UI (SPA, vanilla JS + Bootstrap)
├── shell/                       # hgai interactive CLI shell
├── scripts/                     # MongoDB cold-start and seed scripts
├── tests/                       # pytest test suite
│   ├── test_engine.py           # Hyperkey tests
│   ├── test_query.py            # HQL parser/validator tests
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
python scripts/seed_data.py     # load hello-world example data
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

### 4. Seed hello-world data

```bash
docker-compose exec hgai python scripts/seed_data.py
```

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
POST /api/v1/auth/refresh      # Refresh token
GET  /api/v1/auth/me           # Current user info
```

### Hypergraphs
```
GET    /api/v1/graphs                  # List hypergraphs
POST   /api/v1/graphs                  # Create hypergraph
GET    /api/v1/graphs/{id}             # Get hypergraph
PUT    /api/v1/graphs/{id}             # Update hypergraph
DELETE /api/v1/graphs/{id}             # Delete hypergraph
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

### Query
```
POST /api/v1/query             # Execute HQL query
POST /api/v1/query/validate    # Validate HQL (dry-run)
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
POST   /api/v1/meshes/{id}/query        # Execute federated HQL across all mesh servers
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
        "node_id": "moe-howard"
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
| `hgai_query_execute` | Execute an HQL or SHQL query — language auto-detected from top-level key |
| `hgai_query_validate` | Validate an HQL or SHQL query without executing it — returns `language` field |

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
relation         Semantic relation type: 'has-member', 'sibling', 'broader', etc.
members_json     JSON array: [{"node_id": "id", "seq": 0}, ...]
edge_id          Optional human-readable ID (hyperkey auto-generated if omitted)
label            Optional display label
flavor           'hub', 'symmetric', 'direct', 'transitive', or 'inverse-transitive'
attributes_json  JSON document of edge attributes
tags             Comma-separated tags
```

#### `hgai_query_execute`
```
query_yaml  HQL or SHQL query in YAML format — top-level 'hql:' or 'shql:' key
use_cache   Whether to use query result cache (default: true)
```

HQL example:
```yaml
hql:
  from: my-graph
  match:
    type: hyperedge
    relation: has-member
  return:
    - members
    - attributes
```

SHQL example:
```yaml
shql:
  from: my-graph
  where:
    - edge:
        bind: ?e
        relation: has-member
        members:
          - node: { bind: ?stooge, type: Person }
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
        "node_id": "moe-howard"
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

node = asyncio.run(get_node("hello-world", "moe-howard"))
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
        "text": "{\"id\": \"moe-howard\", \"graph_id\": \"hello-world\", \"label\": \"Moe Howard\", \"type\": \"Person\", \"attributes\": {\"born\": \"1897-06-19\", \"role\": \"Leader\"}, \"tags\": [\"stooge\", \"original\"], \"status\": \"active\", \"valid_from\": null, \"valid_to\": null}"
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
    "relation": "has-member",
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
    "relation": "has-member",
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

#### Execute an HQL Query

```json
{
  "name": "hgai_query_execute",
  "arguments": {
    "query_yaml": "hql:\n  from: hello-world\n  match:\n    type: hypernode\n    node_type: Person\n  return:\n    - id\n    - label\n    - attributes\n  limit: 50",
    "use_cache": true
  }
}
```

#### Execute an SHQL Query

```json
{
  "name": "hgai_query_execute",
  "arguments": {
    "query_yaml": "shql:\n  from: hello-world\n  where:\n    - node:\n        bind: ?person\n        type: Person\n    - edge:\n        bind: ?membership\n        relation: has-member\n        members:\n          - node: { bind: ?person }\n  select:\n    - ?person.id\n    - ?person.label\n    - ?membership.relation\n  limit: 100",
    "use_cache": true
  }
}
```

#### Validate a Query

```json
{
  "name": "hgai_query_validate",
  "arguments": {
    "query_yaml": "hql:\n  from: hello-world\n  match:\n    type: hyperedge\n    relation: has-member\n  return:\n    - members\n    - attributes"
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
    "query_yaml": "hql:\n  from: alpha-bravo-mesh\n  match:\n    type: hypernode\n    node_type: Person\n  return:\n    - id\n    - label\n    - attributes\n  limit: 100",
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

query                           Run HQL query (paste YAML, end with EOF)
query -f <file>                 Run HQL query from file

import -f <file>                Import nodes/edges from YAML file
export -o <file>                Export current graph to YAML file

help [command]                  Show help
exit                            Exit shell
```

---

## Web UI

The web UI is served at `http://localhost:8357/ui/` (local dev) or `http://localhost:8000/ui/` (Docker) and provides:

- **Login** — secure authentication
- **Dashboard** — graph overview with counts and activity
- **Hypergraphs** — list and manage hypergraphs
- **Hypernodes** — full CRUD with attribute editing
- **Hyperedges** — full CRUD with member management
- **Query** — interactive HQL query editor with results visualization
- **Admin** — account management, server info (admin role only)

---

## Inferencing

HypergraphAI's inference engine (`hgai/core/inference.py`) derives implicit knowledge from the relationships explicitly stored in the hypergraph. Inferencing operates at query time and does not mutate stored data — inferred results are returned alongside real results, annotated with `_inferred: true`.

### SKOS Semantic Inferencing

SKOS (Simple Knowledge Organization System) inferencing — hierarchical (`broader`/`narrower`) and associative (`related`) concept relationships — is planned for a future release. It will be implemented via hyperedge hub relations rather than as fields on hypernodes.

### Inverse Edge Inferencing

When a `RelationType` hypernode defines an `inverse` attribute, HypergraphAI can generate the logical inverse of any hyperedge that uses that relation — without storing it explicitly.

For example, if the `has-member` relation node has `attributes.inverse = "member-of"`, then an edge asserting `three-stooges has-member moe-howard` automatically implies an inferred edge asserting `moe-howard member-of three-stooges`.

Inverse edges are returned with `_inferred: true` and `_source_edge` pointing back to the original.

### Transitive Relation Checking

The engine supports checking whether a transitive relation path exists between any two nodes across a set of hypergraphs. This is a reachability query: given a `start_id`, an `end_id`, and a `relation`, it performs a breadth-first walk through all hyperedges of that relation type to determine if the two nodes are transitively connected.

This supports `transitive` and `inverse-transitive` edge flavors in HQL queries.

### Edge Flavors and Inferencing

Hyperedge `flavor` declares the inferencing semantics the relationship supports:

| Flavor | Semantics |
|---|---|
| `hub` | One-to-many (no transitive inference) |
| `symmetric` | All members are equivalent; A→B implies B→A |
| `direct` | Directed from first member to last (no transitivity) |
| `transitive` | A→B and B→C implies A→C (transitive closure) |
| `inverse-transitive` | Transitive closure in reverse direction |

### Roadmap

The following inferencing capabilities are planned for future releases:

- **SKOS inferencing via hyperedge hub relations** — `broader`, `narrower`, and `related` concept hierarchies expressed as typed hyperedges, with transitive closure at query time
- **HQL `infer:` clause** — explicit inference directives inside HQL queries (e.g., `infer: transitive`)
- **Rule-based inferencing** — user-defined inference rules stored as hypernodes of type `InferenceRule`, evaluated at query time
- **Cross-graph inferencing** — SKOS closure and transitive walks spanning multiple hypergraphs in a logical composition or mesh
- **Materialized inference cache** — optional pre-computation of common transitive closures, stored in `query_cache` and invalidated on edge mutations
- **OWL-lite property chains** — support for `owl:propertyChainAxiom`-style inference, where a chain of relations implies a derived relation

---

## SHQL — Semantic Hypergraph Query Language

SHQL (pronounced *"shekel"*) is a second query language for HypergraphAI, implemented as a pluggable module (`hgai_module_shql`). While HQL is a filter-and-aggregate language modelled after MongoDB queries, SHQL is a **pattern-matching** language inspired by SPARQL — designed for multi-hop traversal and implicit joins across hypernodes and hyperedges.

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

Returns all hyperedge group + members

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

### Mesh HQL

Like Mesh SHQL, all servers are queried **concurrently**. Dot-notation refs also fan out concurrently within the same `asyncio.gather` call.

#### Dot-notation `from:` reference formats

| Format | Meaning |
|--------|---------|
| `mesh.server.graph` | Unowned graph on a specific server |
| `mesh.server.space.graph` | Space-scoped graph on a specific server |
| `mesh.*.graph` | Unowned graph on all servers in the mesh |
| `mesh.*.space.graph` | Space-scoped graph on all servers in the mesh |
| `mesh.server.*` | All unowned graphs on a specific server |

Dots are prohibited in all ID fields, so splitting on `.` is unambiguous. The third component is the space ID for 4-part refs or the graph ID for 3-part refs.

**Local graph notation in HQL/SHQL `from:`:**

| Format | Meaning |
|--------|---------|
| `graph_id` | Unowned local graph (`space_id` is null) |
| `space_id/graph_id` | Space-scoped local graph (slash separator) |

The slash separator is used for local space refs; dots remain reserved for mesh routing only.

```yaml
hql:
  from: alpha-bravo-mesh
  match:
    type: hypernode
    node_type: Person
  return:
    - id
    - label
    - type
    - attributes
    - tags
  limit: 500
```

### HQL vs SHQL

| | HQL | SHQL |
|---|---|---|
| Style | Filter / aggregation | Pattern matching |
| Variables | No | Yes (`?var`) |
| Implicit joins | No | Yes — shared `?var` across patterns |
| Multi-hop traversal | No | Yes |
| Inspired by | MongoDB query API | SPARQL |
| Use when | Simple filters, aggregations, PIT queries | Graph traversal, cross-entity joins, relationship discovery |

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
  order_by: ?var.field          # optional sort key
  limit: 100                    # default 500
  offset: 0
  distinct: true                # deduplicate result rows
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
      born: { $lt: "1910-01-01" }   # MongoDB operators work here
```

### Edge Pattern

```yaml
- edge:
    bind: ?edge         # bind matched edge to this variable
    relation: has-member
    flavor: hub
    tags: [original]
    attributes:
      era: classic
    members:            # member patterns (order-independent)
      - node: { bind: ?group, id: three-stooges }
      - node: { bind: ?stooge }     # bind any other member
```

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

All examples use the `hello-world` seed data (Three Stooges).

#### 1. Find all Person hypernodes

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
    - ?person.attributes
  where:
    - node:
        bind: ?person
        type: Person
  order_by: ?person.label
  as: all_people
```

#### 2. Find which hyperedges contain a specific node (Moe Howard)

```yaml
shql:
  from: hello-world
  select:
    - ?edge.id
    - ?edge.relation
    - ?edge.attributes
  where:
    - edge:
        bind: ?edge
        members:
          - node: { id: moe-howard }
  as: moes_edges
```

#### 3. Multi-hop join — find all stooges in the classic era lineup

Variables `?stooge` and `?edge` are bound across node and edge patterns; the
shared variable is the implicit join key.

```yaml
shql:
  from: hello-world
  select:
    - ?stooge.id
    - ?stooge.label
    - ?edge.attributes.era
  where:
    - edge:
        bind: ?edge
        relation: has-member
        attributes:
          era: classic
        members:
          - node: { bind: ?group, id: three-stooges }
          - node: { bind: ?stooge, type: Person }
  order_by: ?stooge.label
  as: classic_stooges
```

#### 4. FILTER on attribute value

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
    - ?person.attributes.born
  where:
    - node:
        bind: ?person
        type: Person
    - filter: "?person.attributes.born < '1900-01-01'"
  as: born_before_1900
```

#### 5. OPTIONAL — include sibling edges where they exist

```yaml
shql:
  from: hello-world
  select:
    - ?person.label
    - ?sibling_edge.relation
  where:
    - node:
        bind: ?person
        type: Person
    - optional:
        - edge:
            bind: ?sibling_edge
            relation: sibling
            members:
              - node: { bind: ?person }
  as: people_with_optional_siblings
```

#### 6. UNION — people born before 1900 OR named "Curly"

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
  where:
    - union:
        - patterns:
            - node:
                bind: ?person
                type: Person
            - filter: "?person.attributes.born < '1900-01-01'"
        - patterns:
            - node:
                bind: ?person
                type: Person
            - filter: "CONTAINS(?person.label, 'Curly')"
  distinct: true
  as: union_result
```

#### 7. Point-in-time query — who was a stooge in 1940?

```yaml
shql:
  from: hello-world
  at: "1940-06-01T00:00:00Z"
  select:
    - ?stooge.label
    - ?edge.attributes
  where:
    - edge:
        bind: ?edge
        relation: has-member
        members:
          - node: { id: three-stooges }
          - node: { bind: ?stooge, type: Person }
  as: stooges_in_1940
```

### Space-scoped Graph References

Space-scoped graphs use the same slash-separator syntax as HQL: `space_id/graph_id`. Unowned graphs are referenced by bare `graph_id`.

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
        relation: has-member
        members:
          - node: { bind: ?person }
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
    - ?edge.attributes
  where:
    - edge:
        bind: ?edge
        relation: has-member
        members:
          - node: { bind: ?stooge, type: Person }
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

**HQL/SHQL `from:` for space-scoped graphs** use slash notation:

```yaml
hql:
  from: my-team/my-graph       # space-scoped
  match:
    type: hyperedge
```

```yaml
hql:
  from:
    - my-team/my-graph         # space-scoped
    - other-team/my-graph      # same graph ID, different space
    - unowned-graph            # unowned (no space)
```

**Mesh dot-notation for space-scoped remote graphs** uses 4 components:

```yaml
hql:
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
| `graph_type` | `hypergraph_id, type` | — | `node_type` filter in HQL/SHQL |
| `tags` | `tags` | multikey | Tag `$all` filter |
| `label` | `label` | — | Label regex/text search |
| `graph_pit` | `hypergraph_id, valid_from, valid_to` | sparse | Point-in-time queries |

#### hyperedges

| Index | Fields | Options | Purpose |
|-------|--------|---------|---------|
| `id_graph_unique` | `id, hypergraph_id` | unique | Edge lookup by ID |
| `hyperkey_graph_unique` | `hyperkey, hypergraph_id` | unique | Hyperkey lookup; enforces semantic deduplication at DB level |
| `graph_status` | `hypergraph_id, status` | — | Hot path — used on every edge list query |
| `graph_relation` | `hypergraph_id, relation` | — | Relation filter in HQL/SHQL |
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
| `federated_hql` | N servers × query time | ~1× query time |
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
