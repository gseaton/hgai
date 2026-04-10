"""Mesh engine — active mesh operations for HypergraphAI."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yaml

from hgai.config import get_settings
from hgai.db.storage import get_storage
from hgai.models.common import now_utc

from .models import MeshServer

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 10.0

# ── Shared HTTP client ────────────────────────────────────────────────────────
# One AsyncClient instance is reused across all mesh requests so that TCP
# connections and TLS sessions are pooled rather than recreated per call.
# Call init_http_client() at startup and close_http_client() at shutdown.

_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Return the shared AsyncClient, creating it lazily if needed."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT,
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
        )
    return _http_client


async def close_http_client() -> None:
    """Close and release the shared AsyncClient. Called at application shutdown."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
    _http_client = None
    logger.info("Mesh HTTP client closed")


def _is_local(server: MeshServer) -> bool:
    """Return True when the server entry refers to this running instance.

    Matches by server_id first, then falls back to URL — covering the case
    where the mesh entry uses a different server_id than the local settings.
    """
    settings = get_settings()
    if server.server_id == settings.server_id:
        return True
    from urllib.parse import urlparse
    try:
        parsed = urlparse(server.url)
        local_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return parsed.hostname in local_hosts and port == settings.port
    except Exception:
        return False


async def _local_graph_ids() -> List[str]:
    """Return all active instantiated graph IDs from the local storage."""
    from hgai_module_storage.filters import HypergraphFilters
    _, graphs = await get_storage().hypergraphs.list(
        HypergraphFilters(status="active"), skip=0, limit=10000
    )
    return [g.id for g in graphs]


def _headers(server: MeshServer) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if server.api_token:
        headers["Authorization"] = f"Bearer {server.api_token}"
    return headers


async def ping_server(server: MeshServer) -> Dict[str, Any]:
    """Health-check a remote hgai server. Returns status dict."""
    try:
        r = await get_http_client().get(
            f"{server.url.rstrip('/')}/health", headers=_headers(server)
        )
        r.raise_for_status()
        return {"server_id": server.server_id, "reachable": True, "detail": r.json()}
    except Exception as e:
        return {"server_id": server.server_id, "reachable": False, "detail": str(e)}


async def fetch_remote_graphs(server: MeshServer, space_id: Optional[str] = None) -> List[str]:
    """Fetch the list of graph IDs available on a remote hgai server.

    When space_id is given, fetches only graphs within that space.
    """
    try:
        if space_id:
            url = f"{server.url.rstrip('/')}/api/v1/spaces/{space_id}/graphs"
        else:
            url = f"{server.url.rstrip('/')}/api/v1/graphs"
        r = await get_http_client().get(url, headers=_headers(server), params={"limit": 500})
        r.raise_for_status()
        data = r.json()
        return [g["id"] for g in data.get("items", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch graphs from {server.server_id}: {e}")
        return []


async def sync_mesh_graphs(mesh_id: str) -> Dict[str, Any]:
    """Refresh the graphs list on each server in a mesh from the live remotes.

    All remote fetches run concurrently via asyncio.gather.
    """
    doc = await get_storage().meshes.get(mesh_id)
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    srv_data_list = doc.get("servers", [])
    servers = [MeshServer(**sd) for sd in srv_data_list]

    graph_lists = await asyncio.gather(*[fetch_remote_graphs(s) for s in servers])

    updated_servers = []
    for srv_data, graphs in zip(srv_data_list, graph_lists):
        srv_data["graphs"] = graphs
        updated_servers.append(srv_data)

    await get_storage().meshes.update_servers(mesh_id, updated_servers)
    return {"mesh_id": mesh_id, "servers_synced": len(updated_servers)}


async def ping_mesh(mesh_id: str) -> List[Dict[str, Any]]:
    """Health-check all servers in a mesh concurrently. Returns a status list."""
    doc = await get_storage().meshes.get(mesh_id)
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    servers = [MeshServer(**sd) for sd in doc.get("servers", [])]
    results = await asyncio.gather(*[ping_server(s) for s in servers])
    return list(results)


async def _graphs_for_server(server: MeshServer) -> List[str]:
    """Return the server's graph IDs, fetching them live if the cached list is empty."""
    if server.graphs:
        return server.graphs
    if _is_local(server):
        return await _local_graph_ids()
    return await fetch_remote_graphs(server)


def _rewrite_from(query_text: str, lang: str, graphs: List[str]) -> str:
    """Parse an HQL/SHQL YAML document, replace the 'from' field with graphs, re-serialize."""
    try:
        doc = yaml.safe_load(query_text)
        if isinstance(doc, dict) and lang in doc:
            doc[lang]["from"] = graphs[0] if len(graphs) == 1 else graphs
        return yaml.dump(doc, default_flow_style=False, allow_unicode=True)
    except Exception:
        return query_text  # fall back to original on any parse error


async def _query_server(
    server: MeshServer,
    graph_ids: List[str],
    query_text: str,
    lang: str,
    use_cache: bool,
) -> Dict[str, Any]:
    """Execute a query on one server for specific graph IDs.

    Returns {'server_id': ..., 'items': [...]} on success.
    Raises on failure so the caller can handle via return_exceptions=True.
    """
    rewritten = _rewrite_from(query_text, lang, graph_ids)
    if _is_local(server):
        if lang == "hql":
            from hgai_module_hql.engine import execute_hql
            result = await execute_hql(rewritten, use_cache=use_cache)
            items = result.items
        else:
            from hgai_module_shql.engine import execute_shql
            result = await execute_shql(rewritten, use_cache=use_cache)
            items = result.items
    else:
        endpoint = "/api/v1/query" if lang == "hql" else "/api/v1/shql/query"
        body: Dict[str, Any] = {lang: rewritten, "use_cache": use_cache}
        r = await get_http_client().post(
            f"{server.url.rstrip('/')}{endpoint}",
            headers=_headers(server),
            json=body,
        )
        r.raise_for_status()
        items = r.json().get("items", [])

    for item in items:
        item["_mesh_server_id"] = server.server_id
    return {"server_id": server.server_id, "items": items}


def _parse_dot_ref(ref: str) -> Optional[tuple]:
    """Parse a dot-notation from: ref into a uniform 4-tuple.

    Formats:
      mesh.server.graph       → (mesh, server, None, graph)   — unowned graph
      mesh.server.space.graph → (mesh, server, space, graph)  — space-scoped graph
      mesh.*.graph            → (mesh, *, None, graph)         — wildcard server, unowned
      mesh.*.space.graph      → (mesh, *, space, graph)        — wildcard server, space-scoped
      mesh.server.*           → (mesh, server, None, *)        — all unowned graphs on server

    Returns None for anything else (treated as a local or space/graph ref).
    """
    parts = ref.split(".")
    if len(parts) == 3:
        return (parts[0], parts[1], None, parts[2])
    if len(parts) == 4:
        return (parts[0], parts[1], parts[2], parts[3])
    return None


async def _graphs_for_server_scoped(
    server: MeshServer, space_id: Optional[str]
) -> List[str]:
    """Return graph IDs for a server, optionally scoped to a space."""
    if space_id:
        if _is_local(server):
            from hgai_module_storage.filters import HypergraphFilters
            _, graphs = await get_storage().hypergraphs.list(
                HypergraphFilters(status="active", space_id=space_id), skip=0, limit=10000
            )
            return [g.id for g in graphs]
        return await fetch_remote_graphs(server, space_id=space_id)
    return await _graphs_for_server(server)


async def resolve_dot_refs(
    refs: List[str],
) -> Tuple[List[str], List[Tuple[MeshServer, List[str]]]]:
    """Resolve dot-notation from: refs into a local-ID list and a mesh routing list.

    Returns (local_graph_ids, [(MeshServer, [graph_ids_or_space/graph_ids]), ...])

    Formats handled:
      mesh.server.graph        — unowned graph on specific server
      mesh.server.space.graph  — space-scoped graph on specific server
      mesh.*.graph / mesh.*.space.graph — wildcard server expansion
      mesh.server.*            — all (unowned) graphs on server

    Wildcards ('*') are expanded against the server's known graph list.
    Mesh document lookups and per-server graph fetches run concurrently.
    Multiple refs that resolve to the same server are merged.
    """
    local_ids: List[str] = []
    parsed_refs: List[Tuple[str, Tuple[str, str, Optional[str], str]]] = []

    for ref in refs:
        parsed = _parse_dot_ref(ref)
        if parsed is None:
            local_ids.append(ref)
        else:
            parsed_refs.append((ref, parsed))

    if not parsed_refs:
        return local_ids, []

    # Fetch all unique mesh docs concurrently
    unique_mesh_ids = list({p[1][0] for p in parsed_refs})
    mesh_docs = await asyncio.gather(
        *[get_storage().meshes.get(mid) for mid in unique_mesh_ids]
    )
    mesh_map: Dict[str, Any] = {
        mid: doc for mid, doc in zip(unique_mesh_ids, mesh_docs) if doc
    }

    # Expand refs into unique (server_id, space_id) pairs that need graph resolution
    server_map: Dict[str, MeshServer] = {}
    expansions: List[Tuple[str, Optional[str], str]] = []  # (server_id, space_id, graph_pat)

    for ref, (mesh_id, server_pat, space_id, graph_pat) in parsed_refs:
        mesh_doc = mesh_map.get(mesh_id)
        if not mesh_doc:
            logger.warning(f"Mesh not found for dot-ref '{ref}' — skipped")
            continue
        for srv_data in mesh_doc.get("servers", []):
            server = MeshServer(**srv_data)
            if server_pat != "*" and server.server_id != server_pat:
                continue
            server_map[server.server_id] = server
            expansions.append((server.server_id, space_id, graph_pat))

    if not server_map:
        return local_ids, []

    # Fetch graphs for all unique (server, space) combos concurrently
    unique_combos = list({(sid, sp) for sid, sp, _ in expansions})
    graph_lists = await asyncio.gather(
        *[_graphs_for_server_scoped(server_map[sid], sp) for sid, sp in unique_combos]
    )
    combo_graphs: Dict[Tuple[str, Optional[str]], List[str]] = dict(
        zip(unique_combos, graph_lists)
    )

    # Build routing table: graph refs are "space/graph" for space-scoped, plain for unowned
    routing: Dict[str, Tuple[MeshServer, List[str]]] = {}
    for server_id, space_id, graph_pat in expansions:
        available = combo_graphs[(server_id, space_id)]
        matched = available if graph_pat == "*" else [g for g in available if g == graph_pat]
        if not matched:
            continue
        # Encode space context into the graph ref for _rewrite_from
        refs_to_add = [
            f"{space_id}/{g}" if space_id else g
            for g in matched
        ]
        if server_id not in routing:
            routing[server_id] = (server_map[server_id], [])
        existing = routing[server_id][1]
        for r in refs_to_add:
            if r not in existing:
                existing.append(r)

    return local_ids, list(routing.values())


async def execute_dot_refs(
    refs: List[str],
    query_text: str,
    lang: str,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Execute a query across dot-notation mesh refs concurrently and merge results.

    lang: 'hql' or 'shql'
    Returns {'count': int, 'items': [...], 'errors': [...]}
    """
    _local_ids, routing = await resolve_dot_refs(refs)

    active = [(s, g) for s, g in routing if g]
    if not active:
        return {"count": 0, "items": [], "errors": []}

    results = await asyncio.gather(
        *[_query_server(s, g, query_text, lang, use_cache) for s, g in active],
        return_exceptions=True,
    )

    all_items: List[Dict] = []
    errors: List[Dict] = []
    for (server, _), result in zip(active, results):
        if isinstance(result, Exception):
            errors.append({"server_id": server.server_id, "error": str(result)})
            logger.warning(f"Dot-ref {lang.upper()} query failed on {server.server_id}: {result}")
        else:
            all_items.extend(result["items"])

    return {"count": len(all_items), "items": all_items, "errors": errors}


async def federated_shql(mesh_id: str, shql_text: str, use_cache: bool = True) -> Dict[str, Any]:
    """Fan out an SHQL query to all servers in a mesh concurrently and merge results."""
    doc = await get_storage().meshes.get(mesh_id)
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    servers = [MeshServer(**sd) for sd in doc.get("servers", [])]

    # Resolve graph lists for all servers concurrently
    graph_lists = await asyncio.gather(*[_graphs_for_server(s) for s in servers])

    active: List[Tuple[MeshServer, List[str]]] = []
    for server, graphs in zip(servers, graph_lists):
        if not graphs:
            logger.warning(f"No graphs on {server.server_id}, skipping")
            continue
        active.append((server, graphs))

    results = await asyncio.gather(
        *[_query_server(s, g, shql_text, "shql", use_cache) for s, g in active],
        return_exceptions=True,
    )

    all_items: List[Dict] = []
    errors: List[Dict] = []
    for (server, _), result in zip(active, results):
        if isinstance(result, Exception):
            errors.append({"server_id": server.server_id, "error": str(result)})
            logger.warning(f"Federated SHQL failed on {server.server_id}: {result}")
        else:
            all_items.extend(result["items"])

    return {
        "mesh_id": mesh_id,
        "count": len(all_items),
        "items": all_items,
        "errors": errors,
    }


async def proxy_request(
    mesh_id: str,
    server_id: str,
    method: str,
    path: str,
    body: Any = None,
    params: Dict[str, str] = None,
) -> Dict[str, Any]:
    """Forward a request to a specific server in a mesh and return the response."""
    doc = await get_storage().meshes.get(mesh_id)
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    server = next(
        (MeshServer(**s) for s in doc.get("servers", []) if s.get("server_id") == server_id),
        None,
    )
    if not server:
        raise ValueError(f"Server '{server_id}' not found in mesh '{mesh_id}'")

    url = f"{server.url.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = await get_http_client().request(
            method=method.upper(),
            url=url,
            headers=_headers(server),
            json=body,
            params=params or {},
        )
        try:
            return {"status_code": r.status_code, "body": r.json()}
        except Exception:
            return {"status_code": r.status_code, "body": r.text}
    except Exception as e:
        raise ValueError(f"Proxy request to {server_id} failed: {e}")


async def federated_hql(mesh_id: str, hql_text: str, use_cache: bool = True) -> Dict[str, Any]:
    """Fan out an HQL query to all servers in a mesh concurrently and merge results."""
    doc = await get_storage().meshes.get(mesh_id)
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    servers = [MeshServer(**sd) for sd in doc.get("servers", [])]

    # Resolve graph lists for all servers concurrently
    graph_lists = await asyncio.gather(*[_graphs_for_server(s) for s in servers])

    active: List[Tuple[MeshServer, List[str]]] = []
    for server, graphs in zip(servers, graph_lists):
        if not graphs:
            logger.warning(f"No graphs on {server.server_id}, skipping")
            continue
        active.append((server, graphs))

    results = await asyncio.gather(
        *[_query_server(s, g, hql_text, "hql", use_cache) for s, g in active],
        return_exceptions=True,
    )

    all_items: List[Dict] = []
    errors: List[Dict] = []
    for (server, _), result in zip(active, results):
        if isinstance(result, Exception):
            errors.append({"server_id": server.server_id, "error": str(result)})
            logger.warning(f"Federated HQL failed on {server.server_id}: {result}")
        else:
            all_items.extend(result["items"])

    return {
        "mesh_id": mesh_id,
        "count": len(all_items),
        "items": all_items,
        "errors": errors,
    }
