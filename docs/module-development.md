# HypergraphAI Module Development Guide

HypergraphAI is modular by design. Every subsystem — security, core operations, inferencing, import/export — is a module. Third parties can extend HypergraphAI by creating and deploying custom modules.

---

## Module Architecture

A HypergraphAI module is a Python package that follows a naming convention and implements a standard interface.

### Naming Convention

```
hgai_module_<name>/       # Package directory
  __init__.py             # Required: re-exports the module descriptor class
  module.py               # Required: module descriptor class (name/version/description + get_router())
  api_router.py           # Optional: FastAPI router
  engine.py               # Optional: business logic the router delegates to
  models.py               # Optional: Pydantic data models
```

Existing built-in modules, for reference: `hgai_module_shql` (SHQL query language), `hgai_module_mesh` (cross-server federation), `hgai_module_mcp` (Model Context Protocol tools), `hgai_module_storage` / `hgai_module_storage_mongodb` (pluggable storage backend).

Module names must:
- Use lowercase with underscores: `hgai_module_mymodule`
- Be unique across your HypergraphAI deployment

---

## Minimal Module Structure

There is no shared base class to subclass — a module is any class exposing `name`/`version`/`description` plus a `get_router()` method returning a FastAPI `APIRouter` (a REST-exposing module), or a `get_app()` method returning an ASGI app to `mount()` instead (an HTTP-sub-app module, like MCP — see `hgai_module_mcp/module.py`). `hgai/main.py` imports and registers each module directly; there is no plugin auto-discovery.

### `hgai_module_mymodule/__init__.py`
```python
from .module import MyModule

__all__ = ["MyModule"]
```

### `hgai_module_mymodule/module.py`
```python
"""My HypergraphAI module descriptor."""

class MyModule:
    name = "mymodule"
    version = "0.1.0"
    description = "My custom HypergraphAI module"

    def get_router(self):
        from .api_router import router
        return router
```

---

## Adding API Endpoints

### `hgai_module_mymodule/api_router.py`
```python
from fastapi import APIRouter, Depends
from hgai.core.auth import get_current_account
from hgai.models.account import AccountInDB

router = APIRouter(prefix="/mymodule", tags=["mymodule"])


@router.get("/hello")
async def hello(account: AccountInDB = Depends(get_current_account)):
    return {
        "message": f"Hello from mymodule, {account.username}!",
        "module": "mymodule",
        "version": "0.1.0"
    }


@router.get("/hyperedge-analysis/{graph_id}")
async def analyze_edges(
    graph_id: str,
    account: AccountInDB = Depends(get_current_account),
):
    from hgai.core.engine import list_hyperedges
    _, edges = await list_hyperedges(graph_id, limit=1000)

    # Custom analysis logic
    relation_counts = {}
    for edge in edges:
        rel = edge.relation
        relation_counts[rel] = relation_counts.get(rel, 0) + 1

    return {
        "graph_id": graph_id,
        "total_edges": len(edges),
        "relation_distribution": relation_counts,
    }
```

---

## Adding MCP Tools

### `hgai_module_mymodule/mcp_tools.py`
```python
import json
from hgai_module_mcp.server import mcp  # Use the shared MCP instance


@mcp.tool()
async def mymodule_analyze_graph(graph_id: str) -> str:
    """Analyze a hypergraph and return statistics.

    Args:
        graph_id: The hypergraph identifier to analyze
    """
    from hgai.core.engine import get_hypergraph_stats
    stats = await get_hypergraph_stats(graph_id)
    return json.dumps(stats, indent=2, default=str)


@mcp.tool()
async def mymodule_find_connected_components(graph_id: str) -> str:
    """Find connected components in a hypergraph.

    Args:
        graph_id: The hypergraph identifier
    """
    from hgai.core.engine import list_hyperedges
    _, edges = await list_hyperedges(graph_id, limit=10000)

    # Build adjacency from hyperedges
    components = {}
    for edge in edges:
        member_ids = [m.node_id for m in edge.members]
        if member_ids:
            root = member_ids[0]
            for mid in member_ids[1:]:
                components[mid] = root

    return json.dumps({
        "graph_id": graph_id,
        "component_map": components,
        "component_count": len(set(components.values())),
    }, indent=2)
```

---

## Accessing the Database

HypergraphAI uses a pluggable storage backend system. Modules should access data through the storage abstraction layer rather than any backend-specific driver directly.

### Using the Storage API

```python
from hgai.db.storage import get_storage
from hgai_module_storage.filters import HypernodeFilters, HyperedgeFilters

# List nodes of a specific type
async def my_operation(graph_id: str):
    total, nodes = await get_storage().hypernodes.list(
        HypernodeFilters(hypergraph_id=graph_id, node_type="Person"),
        skip=0,
        limit=100,
    )
    return nodes

# Get a single node
async def get_node(graph_id: str, node_id: str):
    return await get_storage().hypernodes.get(
        hypergraph_id=graph_id, node_id=node_id
    )
```

### Available Stores

| Store | Access | Description |
|---|---|---|
| `hypergraphs` | `get_storage().hypergraphs` | Hypergraph CRUD, stats, space assignment |
| `hypernodes` | `get_storage().hypernodes` | Hypernode CRUD and search |
| `hyperedges` | `get_storage().hyperedges` | Hyperedge CRUD and search |
| `accounts` | `get_storage().accounts` | User/agent account management |
| `spaces` | `get_storage().spaces` | Multi-tenant space management |
| `meshes` | `get_storage().meshes` | Mesh federation registry |
| `cache` | `get_storage().cache` | Query result cache |
| `media` | `get_storage().media` | Binary file metadata (upload/download/delete) |
| `notes` | `get_storage().notes` | Account-owned note documents |

### Aggregation

`hypernodes` and `hyperedges` also expose `aggregate(filters, spec)` and `count(filters)`, which group and reduce server-side instead of returning documents:

```python
from hgai_module_storage.filters import AggregateMeasure as M, AggregateSpec, HypernodeSearchFilters

rows = await get_storage().hypernodes.aggregate(
    HypernodeSearchFilters(hypergraph_ids=["my-graph"]),
    AggregateSpec(
        group_by=["type"],
        measures=[M("count"), M("avg", "attributes.age")],
        order_by=[("count", True)],
        limit=10,
    ),
)
# [{"type": "person", "count": 42, "avg_attributes_age": 31.5}, ...]
```

Functions: `count`, `count_distinct`, `count_numeric` (numeric values only — `avg`'s divisor), `sum`, `avg`, `min`, `max`. Fields are `id`, `type`, `label`, `status`, `relation`, `flavor`, `tags`, `hypergraph_id`, or `attributes.<key>`; anything else raises `AggregateSpecError`. Exact semantics (nulls, `tags` unwinding, ordering) are specified in `hgai_module_storage/aggregate.py`. `count` and aggregates ignore the SHQL candidate caps.

**Writing a storage backend:** you get correct aggregation for free — the base class default pages through `search()` and reduces in Python. Override `aggregate()` (and set `supports_aggregate_pushdown = True`) to push it into your database, then add your backend to `BACKENDS` in `tests/test_storage_aggregate.py`; that conformance suite is what guarantees every backend returns identical rows.

### Ordered paging

`hypernodes` and `hyperedges` also expose `search_ordered(filters, order_by, skip, limit)` — one page of matches sorted by `[(field path, descending), ...]` (same field whitelist as aggregation). Values sort missing/null first, then numbers < strings < objects < arrays < booleans < datetimes; rows tied on every key are ordered by `id` then `hypergraph_id`, so pages never overlap or skip. Semantics live in `hgai_module_storage/ordering.py`.

**Writing a storage backend:** the default implementation streams `search()` and keeps the best `skip + limit` rows (correct anywhere, but scans every match). Override `search_ordered()` and set `supports_ordered_search = True` to sort natively, and add your backend to `BACKENDS` in `tests/storage_fixtures.py` — `tests/test_storage_ordering.py` is the conformance suite.

### Custom Module Storage

If your module needs its own storage, use the active backend's underlying connection. For the MongoDB backend:

```python
from hgai_module_storage_mongodb.connection import get_db

async def my_custom_data():
    db = get_db()
    my_collection = db["mymodule_data"]
    await my_collection.insert_one({"key": "value"})
```

Note: accessing the backend connection directly couples your module to that backend. Prefer using the core engine functions or storage stores where possible.

---

## Working with the Core Engine

```python
from hgai.core.engine import (
    get_hypergraph,
    list_hypernodes,
    list_hyperedges,
    create_hypernode,
    create_hyperedge,
)
from hgai_module_shql.engine import execute_shql
from hgai.core.inference import expand_edge_closure

# Fetch a graph
graph = await get_hypergraph("my-graph")

# List nodes
total, nodes = await list_hypernodes(
    "my-graph",
    node_type="Person",
    status="active",
    limit=100,
)

# Execute SHQL
result = await execute_shql("""
shql:
  from: my-graph
  where:
    - edge:
        bind: ?e
        relation: has-member
  select:
    - ?e.members
""")

# Axiom-driven inferencing — inverse-of/symmetric/superproperty (SKOS
# broader/narrower) expansion over a set of already-fetched fact edges,
# driven entirely by whatever owl:*/skos:* axiom hyperedges exist between
# their relations' RelationType hypernodes (see README § Inferencing)
_, fact_edges = await list_hyperedges("taxonomy", relation="broader")
inferred = await expand_edge_closure(
    [e.model_dump() for e in fact_edges],
    graph_ids=["taxonomy"],
)
```

---

## Module Configuration

Modules can read configuration from environment variables:

```python
import os
from pydantic_settings import BaseSettings

class MyModuleSettings(BaseSettings):
    model_config = {"env_prefix": "HGAI_MYMODULE_"}

    api_key: str = ""
    max_depth: int = 10
    enabled: bool = True
```

Set via environment:
```env
HGAI_MYMODULE_API_KEY=abc123
HGAI_MYMODULE_MAX_DEPTH=5
```

---

## Registering a Module

To register your module with the HypergraphAI server, add it to `create_app()` in `hgai/main.py`, following the pattern used for the built-in `hgai_module_mesh`/`hgai_module_shql`/`hgai_module_mcp` modules — imported and mounted directly, wrapped in a broad `try`/`except` so a missing or broken optional module never prevents the server from starting:

```python
# In create_app() in hgai/main.py, alongside the other module registrations
try:
    from hgai_module_mymodule import MyModule
    my_module = MyModule()
    app.include_router(my_module.get_router(), prefix=prefix)
    logger.info("MyModule mounted at /api/v1/mymodule")
except BaseException as e:
    logger.warning(f"MyModule not available (continuing without it): {type(e).__name__}: {e}")
```

There is no environment-based auto-discovery — every module is imported explicitly in `hgai/main.py`.

---

## Security Considerations

1. **Always use authentication** — import `get_current_account` or `require_admin` from `hgai.core.auth`
2. **Never expose raw backend access** — use `get_storage()` stores or the engine layer
3. **Validate all inputs** — use Pydantic models for all API request bodies
4. **Respect RBAC** — check `can_access_graph()` and `can_perform()` before operations
5. **Sanitize outputs** — never expose password hashes or internal system fields

```python
from hgai.core.auth import get_current_account, require_admin, can_access_graph

# Require admin
@router.get("/admin-only")
async def admin_endpoint(account = Depends(require_admin)):
    ...

# Check graph access
@router.get("/graph-data/{graph_id}")
async def graph_endpoint(graph_id: str, account = Depends(get_current_account)):
    if not await can_access_graph(account, graph_id):
        raise HTTPException(403, "Access denied")
    ...
```

---

## Module Licensing

HypergraphAI core modules are released under the MIT License.

Custom and advanced modules may have any license as determined by their authors.
Document your module's license clearly in its `README.md`.

---

## Example: Embedding Module

A complete example module that adds vector embedding search to HypergraphAI:

```
hgai_module_embeddings/
  __init__.py
  module.py          # EmbeddingsModule: startup/shutdown
  api_router.py      # POST /embeddings/search
  mcp_tools.py       # hgai_embeddings_search tool
  models.py          # EmbeddingSearchRequest, EmbeddingSearchResult
  embedder.py        # Embedding computation logic
  README.md
```

This module would:
1. On node create/update: compute embedding and store it
2. Expose `POST /api/v1/embeddings/search` for semantic similarity search
3. Expose `hgai_embeddings_search` MCP tool for AI agents
