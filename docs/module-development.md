# HypergraphAI Module Development Guide

HypergraphAI is modular by design. Every subsystem — security, core operations, inferencing, import/export — is a module. Third parties can extend HypergraphAI by creating and deploying custom modules.

---

## Module Architecture

A HypergraphAI module is a Python package that follows a naming convention and implements a standard interface.

### Naming Convention

```
hgai_module_<name>/       # Package directory
  __init__.py
  module.py               # Required: HgaiModule subclass
  mcp_tools.py            # Optional: MCP tool definitions
  api_router.py           # Optional: FastAPI router
  models.py               # Optional: Pydantic data models
  README.md               # Required: module documentation
```

Module names must:
- Use lowercase with hyphens: `hgai_module_my-module`
- Be unique across your HypergraphAI deployment
- Not conflict with built-in module names: `core`, `auth`, `cache`, `inference`, `query`

---

## Minimal Module Structure

### `hgai_module_mymodule/__init__.py`
```python
"""My HypergraphAI Module."""

__version__ = "0.1.0"
__module_name__ = "mymodule"
__module_description__ = "My custom HypergraphAI module"
```

### `hgai_module_mymodule/module.py`
```python
"""HypergraphAI module entry point."""

class HgaiModule:
    name: str = "mymodule"
    version: str = "0.1.0"
    description: str = "My custom module"

    async def startup(self, app, db, settings):
        """Called when HypergraphAI server starts."""
        pass

    async def shutdown(self):
        """Called when HypergraphAI server stops."""
        pass


class MyModule(HgaiModule):
    name = "mymodule"
    version = "0.1.0"
    description = "My custom HypergraphAI module"

    async def startup(self, app, db, settings):
        # Register routes, initialize resources, etc.
        from .api_router import router
        app.include_router(router, prefix="/api/v1")
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
from hgai.mcp.server import mcp  # Use the shared MCP instance


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
from hgai.core.query import execute_hql
from hgai.core.inference import get_skos_closure

# Fetch a graph
graph = await get_hypergraph("my-graph")

# List nodes
total, nodes = await list_hypernodes(
    "my-graph",
    node_type="Person",
    status="active",
    limit=100,
)

# Execute HQL
result = await execute_hql("""
hql:
  from: my-graph
  match:
    type: hyperedge
    relation: has-member
  return:
    - members
""")

# SKOS inferencing
broader_concepts = await get_skos_closure(
    node_id="mammal",
    graph_ids=["taxonomy"],
    relation="broader",
    max_depth=5,
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

To register your module with the HypergraphAI server, add it to `hgai/main.py`:

```python
# In create_app() in hgai/main.py
try:
    from hgai_module_mymodule.module import MyModule
    module = MyModule()
    await module.startup(app, get_settings())
except ImportError:
    pass  # Module not installed
```

Or configure via environment for auto-discovery (future feature):
```env
HGAI_MODULES=mymodule,anothermodule
```

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
    if not can_access_graph(account, graph_id):
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
