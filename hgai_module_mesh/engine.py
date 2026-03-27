"""Mesh engine — active mesh operations for HypergraphAI."""

import logging
from typing import Any, Dict, List, Optional

import httpx

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
                f"{server.url.rstrip('/')}/api/v1/hypergraphs",
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


async def federated_hql(mesh_id: str, hql_text: str, use_cache: bool = True) -> Dict[str, Any]:
    """Fan out an HQL query to all servers in a mesh and merge results."""
    doc = await col_meshes().find_one({"id": mesh_id})
    if not doc:
        raise ValueError(f"Mesh not found: {mesh_id}")

    all_items: List[Dict] = []
    errors: List[Dict] = []

    for srv_data in doc.get("servers", []):
        server = MeshServer(**srv_data)
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                r = await client.post(
                    f"{server.url.rstrip('/')}/api/v1/query",
                    headers=_headers(server),
                    json={"hql": hql_text, "use_cache": use_cache},
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
