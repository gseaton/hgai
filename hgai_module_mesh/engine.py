"""Mesh engine — active mesh operations for HypergraphAI."""

import logging
from typing import Any, Dict, List, Optional

import httpx
import yaml

from hgai.db.mongodb import col_meshes
from hgai.models.common import now_utc

from .models import MeshServer

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 10.0


def _headers(server: MeshServer) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if server.api_token:
        headers["Authorization"] = f"Bearer {server.api_token}"
    return headers


async def ping_server(server: MeshServer) -> Dict[str, Any]:
    """Health-check a remote hgai server. Returns status dict."""
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.get(f"{server.url.rstrip('/')}/health", headers=_headers(server))
            r.raise_for_status()
            return {"server_id": server.server_id, "reachable": True, "detail": r.json()}
    except Exception as e:
        return {"server_id": server.server_id, "reachable": False, "detail": str(e)}


async def fetch_remote_graphs(server: MeshServer) -> List[str]:
    """Fetch the list of graph IDs available on a remote hgai server."""
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.get(
                f"{server.url.rstrip('/')}/api/v1/graphs",
                headers=_headers(server),
                params={"limit": 500},
            )
            r.raise_for_status()
            data = r.json()
            return [g["id"] for g in data.get("items", [])]
    except Exception as e:
        logger.warning(f"Failed to fetch graphs from {server.server_id}: {e}")
        return []


async def sync_mesh_graphs(mesh_id: str) -> Dict[str, Any]:
    """Refresh the graphs list on each server in a mesh from the live remotes."""
    doc = await col_meshes().find_one({"id": mesh_id})
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    updated_servers = []
    for srv_data in doc.get("servers", []):
        server = MeshServer(**srv_data)
        graphs = await fetch_remote_graphs(server)
        srv_data["graphs"] = graphs
        updated_servers.append(srv_data)

    await col_meshes().update_one(
        {"id": mesh_id},
        {"$set": {"servers": updated_servers, "system_updated": now_utc()}},
    )
    return {"mesh_id": mesh_id, "servers_synced": len(updated_servers)}


async def ping_mesh(mesh_id: str) -> List[Dict[str, Any]]:
    """Health-check all servers in a mesh. Returns a status list."""
    doc = await col_meshes().find_one({"id": mesh_id})
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    results = []
    for srv_data in doc.get("servers", []):
        server = MeshServer(**srv_data)
        result = await ping_server(server)
        results.append(result)
    return results


async def _graphs_for_server(server: MeshServer) -> List[str]:
    """Return the server's graph IDs, fetching them live if the cached list is empty."""
    if server.graphs:
        return server.graphs
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


async def federated_shql(mesh_id: str, shql_text: str, use_cache: bool = True) -> Dict[str, Any]:
    """Fan out an SHQL query to all servers in a mesh and merge results."""
    doc = await col_meshes().find_one({"id": mesh_id})
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    all_items: List[Dict] = []
    errors: List[Dict] = []

    for srv_data in doc.get("servers", []):
        server = MeshServer(**srv_data)
        graphs = await _graphs_for_server(server)
        if not graphs:
            logger.warning(f"No graphs on {server.server_id}, skipping")
            continue
        rewritten = _rewrite_from(shql_text, "shql", graphs)
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                r = await client.post(
                    f"{server.url.rstrip('/')}/api/v1/shql/query",
                    headers=_headers(server),
                    json={"shql": rewritten, "use_cache": use_cache},
                )
                r.raise_for_status()
                data = r.json()
                for item in data.get("items", []):
                    item["_mesh_server_id"] = server.server_id
                all_items.extend(data.get("items", []))
        except Exception as e:
            errors.append({"server_id": server.server_id, "error": str(e)})
            logger.warning(f"Federated SHQL failed on {server.server_id}: {e}")

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
    doc = await col_meshes().find_one({"id": mesh_id})
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
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.request(
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
    """Fan out an HQL query to all servers in a mesh and merge results."""
    doc = await col_meshes().find_one({"id": mesh_id})
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    all_items: List[Dict] = []
    errors: List[Dict] = []

    for srv_data in doc.get("servers", []):
        server = MeshServer(**srv_data)
        graphs = await _graphs_for_server(server)
        if not graphs:
            logger.warning(f"No graphs on {server.server_id}, skipping")
            continue
        rewritten = _rewrite_from(hql_text, "hql", graphs)
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                r = await client.post(
                    f"{server.url.rstrip('/')}/api/v1/query",
                    headers=_headers(server),
                    json={"hql": rewritten, "use_cache": use_cache},
                )
                r.raise_for_status()
                data = r.json()
                for item in data.get("items", []):
                    item["_mesh_server_id"] = server.server_id
                all_items.extend(data.get("items", []))
        except Exception as e:
            errors.append({"server_id": server.server_id, "error": str(e)})
            logger.warning(f"Federated HQL failed on {server.server_id}: {e}")

    return {
        "mesh_id": mesh_id,
        "count": len(all_items),
        "items": all_items,
        "errors": errors,
    }
