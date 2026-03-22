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
- [Running Locally](#running-locally)
- [Docker Deployment](#docker-deployment)
- [API Reference](#api-reference)
- [MCP Server](#mcp-server)
- [hgai Shell](#hgai-shell)
- [Web UI](#web-ui)
- [Inferencing](#inferencing)
- [SHQL — Semantic Hypergraph Query Language](#shql--semantic-hypergraph-query-language)
- [Module Development](#module-development)
- [Administration](#administration)

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
    relation: holds-office
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
      relation: president-of
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
The `members.node_id` path is handled as a special case in the engine (query.py:117-120), 
translating to a MongoDB `members.node_id` field match —
which works against the array of `member` objects regardless of position.

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

---

## Architecture

```
hgai/
├── hgai/                    # Main Python package
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Settings (env vars, dotenv)
│   ├── db/                  # Database layer (motor/MongoDB)
│   ├── models/              # Pydantic data models
│   ├── core/                # Core engine: query, inference, auth, cache
│   ├── api/                 # REST API routers
│   └── mcp/                 # MCP server and tools
├── ui/                      # Web UI (SPA, vanilla JS + Bootstrap)
├── shell/                   # hgai interactive CLI shell
├── scripts/                 # MongoDB cold-start and seed scripts
└── docs/                    # Documentation

Project Structure                                                                                                                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                                                                    
  hgai/                                                                                                                                                                                                                                                                                                           
  ├── README.md                          # Full developer/admin docs                                                                                                                                                                                                                                                
  ├── LICENSE                            # MIT                                                                                                                                                                                                                                                                      
  ├── .env.example                       # All env vars documented                                                                                                                                                                                                                                                  
  ├── .gitignore                                                                                                                                                                                                                                                                                                    
  ├── docker-compose.yml                 # MongoDB + hgai server                                                                                                                                                                                                                                                  
  ├── Dockerfile                                                                                                                                                                                                                                                                                                    
  ├── requirements.txt / pyproject.toml                                                                                                                                                                                                                                                                           
  │                                                                                                                                                                                                                                                                                                                 
  ├── scripts/                                                                                                                                                                                                                                                                                                      
  │   ├── mongo-init.js                  # Cold-start: admin/pwd357, all collections + indexes
  │   └── seed_data.py                   # Hello-world Three Stooges example data                                                                                                                                                                                                                                   
  │                                                                                                                                                                                                                                                                                                                 
  ├── hgai/                              # Python package                                                                                                                                                                                                                                                           
  │   ├── main.py                        # FastAPI app, lifespan, MCP mount, UI static                                                                                                                                                                                                                              
  │   ├── config.py                      # pydantic-settings (HGAI_ prefix)                                                                                                                                                                                                                                         
  │   ├── db/mongodb.py                  # motor async connection + collection accessors                                                                                                                                                                                                                            
  │   ├── models/                        # Pydantic models: hypernode, hyperedge, hypergraph, account, mesh                                                                                                                                                                                                         
  │   ├── core/                                                                                                                                                                                                                                                                                                     
  │   │   ├── engine.py                  # Hypernode/edge/graph CRUD, hyperkey generation, import/export                                                                                                                                                                                                            
  │   │   ├── query.py                   # HQL parser + executor (YAML, PIT, multi-graph, aggregation)                                                                                                                                                                                                              
  │   │   ├── inference.py               # SKOS broader/narrower/related transitive closure                                                                                                                                                                                                                         
  │   │   ├── auth.py                    # JWT, bcrypt, RBAC, bootstrap admin                                                                                                                                                                                                                                       
  │   │   └── cache.py                   # MongoDB-backed query cache with TTL                                                                                                                                                                                                                                      
  │   ├── api/routers/                   # auth, hypergraphs, hypernodes, hyperedges, query, accounts, meshes                                                                                                                                                                                                       
  │   └── mcp/server.py                  # FastMCP server with 15 tools (all CRUD + HQL query)                                                                                                                                                                                                                      
  │                                                                                                                                                                                                                                                                                                                 
  ├── ui/                                                                                                                                                                                                                                                                                                           
  │   ├── index.html                     # Full SPA: login, dashboard, all CRUD screens, query, admin                                                                                                                                                                                                               
  │   ├── css/hgai.css                   # Complete dark sidebar + responsive layout                                                                                                                                                                                                                                
  │   └── js/                                                                                                                                                                                                                                                                                                       
  │       ├── api.js                     # API client (all endpoints)                                                                                                                                                                                                                                               
  │       └── app.js                     # All screen logic, modals, pagination, HQL editor                                                                                                                                                                                                                         
  │                                                                                                                                                                                                                                                                                                                 
  ├── shell/hgai_shell.py               # Interactive CLI shell with history, all commands                                                                                                                                                                                                                          
  │                                                                                                                                                                                                                                                                                                                 
  ├── docs/                                                                                                                                                                                                                                                                                                         
  │   ├── concepts.md                    # Hypergraph concepts, HQL reference, SKOS, RBAC
  │   ├── hello-world.md                 # Step-by-step first hypergraph tutorial                                                                                                                                                                                                                                   
  │   ├── module-development.md          # Third-party module development guide                                                                                                                                                                                                                                     
  │   └── api-reference.md               # Full REST + MCP API reference                                                                                                                                                                                                                                            
  │                                                                                                                                                                                                                                                                                                                 
  └── tests/                                                                                                                                                                                                                                                                                                        
      ├── test_engine.py                 # Hyperkey tests                                                                                                                                                                                                                                                           
      └── test_query.py                  # HQL parser/validator tests                                                                                                                                                                                                                                               
```   
To Run                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                  
### Docker (recommended)                                                                                                                                                                                                                                                                                            
cp .env.example .env                                                                                                                                                                                                                                                                                              
docker-compose up -d                                                                                                                                                                                                                                                                                              
python scripts/seed_data.py     # load hello-world example data                                                                                                                                                                                                                                                   
                                                                                                                                                                                                                                                                                                        
### Local dev                                                                                                                                                                                                                                                                                                       
pip install -r requirements.txt                                                                                                                                                                                                                                                                                   
uvicorn hgai.main:app --reload                                                                                                                                                                                                                                                                                    

- Web UI: http://localhost:8000/ui/ — login: admin / pwd357                                                                                                                                                                                                                                                       
- API docs: http://localhost:8000/api/docs                                                                                                                                                                                                                                                                      
- MCP server: http://localhost:8000/mcp/                                                                                                                                                                                                                                                                          
- Shell:                      
  - $ python shell/hgai_shell.py
  - $ python shell/hgai_shell.py --server http://localhost:8000 --user admin
  - $ python shell/hgai_shell.py --server http://myserver:8000 -u myuser -p mypassword

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
| `HGAI_MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection URI |
| `HGAI_MONGO_DB` | `hgai` | MongoDB database name |
| `HGAI_SECRET_KEY` | *(required)* | JWT signing secret |
| `HGAI_TOKEN_EXPIRE_MINUTES` | `480` | JWT token lifetime |
| `HGAI_HOST` | `0.0.0.0` | Server bind host |
| `HGAI_PORT` | `8000` | Server bind port |
| `HGAI_LOG_LEVEL` | `info` | Log level |
| `HGAI_CACHE_TTL_SECONDS` | `300` | Query cache TTL |
| `HGAI_CACHE_ENABLED` | `true` | Enable query caching |
| `HGAI_SERVER_ID` | `hgai-local` | Server identifier (for meshes) |
| `HGAI_SERVER_NAME` | `HypergraphAI Local` | Server display name |

---

## Running Locally

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
uvicorn hgai.main:app --reload --host 0.0.0.0 --port 8000

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

Base URL: `http://localhost:8000/api/v1`

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

---

## MCP Server

HypergraphAI exposes all operations as MCP (Model Context Protocol) server tools at:

```
http://localhost:8000/mcp/
```

MCP server groups:
- `hgai-core` — hypergraph, hypernode, hyperedge CRUD
- `hgai-query` — HQL query execution
- `hgai-admin` — account and server management

Configure your MCP client (e.g., Claude Desktop):
```json
{
  "mcpServers": {
    "hgai": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer <your-token>"
      }
    }
  }
}
```

---

## hgai Shell

The `hgai` shell provides an interactive CLI for all HypergraphAI operations:

```bash
python shell/hgai_shell.py
```

Or connect to a remote server:
```bash
python shell/hgai_shell.py --server http://myserver:8000 --user admin
```

### Shell Commands

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

The web UI is served at `http://localhost:8000/ui/` and provides:

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

HypergraphAI implements the [SKOS (Simple Knowledge Organization System)](https://www.w3.org/TR/skos-reference/) vocabulary for hierarchical and associative concept relationships. SKOS links are stored directly on hypernodes:

| Field | Meaning |
|---|---|
| `skos_broader` | This node is a narrower concept of the listed nodes (parent concepts) |
| `skos_narrower` | This node is a broader concept of the listed nodes (child concepts) |
| `skos_related` | This node is associatively related to the listed nodes |

**Transitive closure** is computed via breadth-first traversal up to a configurable depth (default: 10 hops). This means if `Dog` → `broader` → `Animal` → `broader` → `LivingThing`, then querying the broader closure of `Dog` returns both `Animal` and `LivingThing`.

Example hypernode with SKOS links:
```json
{
  "id": "dog",
  "label": "Dog",
  "type": "Concept",
  "skos_broader": ["animal"],
  "skos_narrower": ["labrador", "poodle"],
  "skos_related": ["cat"]
}
```

When SKOS inference is applied to a result set, each item gains an `_inferred` field:
```json
{
  "id": "dog",
  "_inferred": {
    "broader_closure": ["animal", "living-thing", "organism"],
    "narrower_closure": ["labrador", "poodle", "guide-dog"]
  }
}
```

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

- **HQL `infer:` clause** — explicit inference directives inside HQL queries (e.g., `infer: skos_broader`, `infer: transitive`)
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
├── __init__.py
├── module.py          # HgaiModule subclass
├── mcp_tools.py       # MCP tool definitions (optional)
├── api_router.py      # FastAPI router (optional)
└── README.md
```

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

---

## License

MIT License — see [LICENSE](LICENSE) for details.

HypergraphAI core engine and modules are open-source under the MIT License.
Custom or advanced modules may have different licensing as determined by their authors.
