"""Tests for the hgai_module_mesh module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Model tests ──────────────────────────────────────────────────────────────

from hgai_module_mesh.models import (
    MeshServer, MeshCreate, MeshUpdate, MeshResponse, MeshInDB,
)
from hgai.models.common import Status


def test_mesh_server_defaults():
    server = MeshServer(server_id="s1", server_name="Server 1", url="http://localhost:8357")
    assert server.graphs == []
    assert server.status == Status.active
    assert server.api_token is None


def test_mesh_create():
    mesh = MeshCreate(id="m1", label="Test Mesh")
    assert mesh.id == "m1"
    assert mesh.servers == []


def test_mesh_update_partial():
    update = MeshUpdate(label="New Label")
    assert update.label == "New Label"
    assert update.servers is None
    assert update.status is None


def test_mesh_response_roundtrip():
    server = MeshServer(server_id="s1", server_name="S1", url="http://host:8357")
    mesh = MeshResponse(id="m1", label="Mesh", servers=[server])
    assert len(mesh.servers) == 1
    assert mesh.servers[0].server_id == "s1"


# ─── Module descriptor tests ──────────────────────────────────────────────────

from hgai_module_mesh import MeshModule


def test_module_attributes():
    m = MeshModule()
    assert m.name == "mesh"
    assert m.version == "0.1.0"
    assert "mesh" in m.description.lower()


def test_module_get_router():
    m = MeshModule()
    router = m.get_router()
    assert router.prefix == "/meshes"
    routes = [r.path for r in router.routes]
    assert "" in routes or "/" in routes or any("/meshes" in r for r in routes)


# ─── Engine tests (mocked MongoDB + HTTP) ────────────────────────────────────

from hgai_module_mesh.engine import ping_server, federated_hql, sync_mesh_graphs


@pytest.mark.asyncio
async def test_ping_server_reachable():
    server = MeshServer(server_id="s1", server_name="S1", url="http://host:8357")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"status": "ok"}

    with patch("hgai_module_mesh.engine.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await ping_server(server)

    assert result["server_id"] == "s1"
    assert result["reachable"] is True
    assert result["detail"] == {"status": "ok"}


@pytest.mark.asyncio
async def test_ping_server_unreachable():
    server = MeshServer(server_id="s1", server_name="S1", url="http://host:8357")

    with patch("hgai_module_mesh.engine.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await ping_server(server)

    assert result["server_id"] == "s1"
    assert result["reachable"] is False
    assert "connection refused" in result["detail"]


@pytest.mark.asyncio
async def test_federated_hql_merges_results():
    mesh_doc = {
        "id": "m1",
        "servers": [
            {"server_id": "s1", "server_name": "S1", "url": "http://host-a:8357",
             "graphs": [], "status": "active", "tags": [], "attributes": {},
             "system_created": None, "system_updated": None, "created_by": None, "version": 1},
            {"server_id": "s2", "server_name": "S2", "url": "http://host-b:8357",
             "graphs": [], "status": "active", "tags": [], "attributes": {},
             "system_created": None, "system_updated": None, "created_by": None, "version": 1},
        ],
    }

    def make_mock_response(items):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json.return_value = {"items": items}
        return r

    mock_mesh_store = MagicMock()
    mock_mesh_store.get = AsyncMock(return_value=mesh_doc)

    mock_storage = MagicMock()
    mock_storage.meshes = mock_mesh_store

    with patch("hgai_module_mesh.engine.get_storage", return_value=mock_storage), \
         patch("hgai_module_mesh.engine.httpx.AsyncClient") as mock_client_cls:

        responses = [
            make_mock_response([{"id": "node-1"}]),
            make_mock_response([{"id": "node-2"}, {"id": "node-3"}]),
        ]
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            r = responses[call_count]
            call_count += 1
            return r

        mock_client = AsyncMock()
        mock_client.post = mock_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await federated_hql("m1", "hql:\n  from: g1\n")

    assert result["mesh_id"] == "m1"
    assert result["count"] == 3
    assert result["errors"] == []
    server_ids = {item["_mesh_server_id"] for item in result["items"]}
    assert server_ids == {"s1", "s2"}


@pytest.mark.asyncio
async def test_federated_hql_mesh_not_found():
    mock_mesh_store = MagicMock()
    mock_mesh_store.get = AsyncMock(return_value=None)
    mock_storage = MagicMock()
    mock_storage.meshes = mock_mesh_store
    with patch("hgai_module_mesh.engine.get_storage", return_value=mock_storage):
        with pytest.raises(ValueError, match="Mesh not found"):
            await federated_hql("nonexistent", "hql:\n  from: g1\n")


@pytest.mark.asyncio
async def test_sync_mesh_graphs_not_found():
    mock_mesh_store = MagicMock()
    mock_mesh_store.get = AsyncMock(return_value=None)
    mock_storage = MagicMock()
    mock_storage.meshes = mock_mesh_store
    with patch("hgai_module_mesh.engine.get_storage", return_value=mock_storage):
        with pytest.raises(ValueError, match="Mesh not found"):
            await sync_mesh_graphs("nonexistent")
