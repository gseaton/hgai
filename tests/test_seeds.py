"""The example hypergraphs shipped in scripts/seeds/ and the loader that installs them.

Seeds are ordinary hypergraph export files, so these tests hold each file to the
export format (parses, is self-contained, imports with no per-item errors) and
check the loader's discovery / selection logic. Talking to a live server is
verified separately against a fresh database."""

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from hgai.core import transfer

ROOT = Path(__file__).resolve().parent.parent
SEEDS = ROOT / "scripts" / "seeds"

_spec = importlib.util.spec_from_file_location("seed_data", ROOT / "scripts" / "seed_data.py")
seed_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_data)

# Members referenced by an edge but not defined in the seed (data as exported;
# an import doesn't require them). Listing them here keeps any *new* dangling
# reference from slipping in unnoticed.
KNOWN_DANGLING_MEMBERS = {"hello-world": {"person:tommy-moore"}}

SEED_FILES = sorted(SEEDS.glob("hgai-hypergraph-*.export.yml"))


def test_the_expected_seeds_are_shipped():
    assert {p.name for p in SEED_FILES} >= {
        "hgai-hypergraph-hello-world.export.yml", "hgai-hypergraph-eden.export.yml",
    }


@pytest.mark.parametrize("path", SEED_FILES, ids=lambda p: p.name)
def test_seed_is_a_valid_self_contained_export(path):
    doc = transfer.parse_export(path.read_text())
    graph_id = doc["graph"]["id"]
    assert path.name == f"hgai-hypergraph-{graph_id}.export.yml"
    assert doc["counts"] == {"nodes": len(doc["nodes"]), "edges": len(doc["edges"])}
    assert doc["nodes"], "a seed with no nodes is pointless"

    node_ids = [n["id"] for n in doc["nodes"]]
    assert len(node_ids) == len(set(node_ids)), "duplicate node ids"
    edge_ids = [e["id"] for e in doc["edges"]]
    assert len(edge_ids) == len(set(edge_ids)), "duplicate edge ids"

    # A member may be a hypernode or another hyperedge (edges are first-class).
    known = set(node_ids) | set(edge_ids)
    dangling = {m["node_id"] for e in doc["edges"] for m in e["members"]} - known
    assert dangling <= KNOWN_DANGLING_MEMBERS.get(graph_id, set()), \
        f"edges reference nodes/edges that are not in the seed: {sorted(dangling)}"

    # portable: no references to media files that only exist on the exporting instance
    assert not [i["id"] for i in doc["nodes"] + doc["edges"] if i.get("media") or i.get("default_media_id")]
    assert not [i["id"] for i in doc["nodes"] + doc["edges"] if i.get("mutations")]


@pytest.mark.parametrize("path", SEED_FILES, ids=lambda p: p.name)
def test_seed_imports_cleanly_into_an_empty_instance(path):
    doc = transfer.parse_export(path.read_text())
    fake = SimpleNamespace(
        get_hypergraph=AsyncMock(return_value=None), create_hypergraph=AsyncMock(),
        get_hypernode=AsyncMock(return_value=None), create_hypernode=AsyncMock(),
        get_hyperedge=AsyncMock(return_value=None), find_duplicate_hyperedge=AsyncMock(return_value=None),
        create_hyperedge=AsyncMock(),
    )
    with patch.object(transfer, "engine", fake):
        result = asyncio.run(transfer.import_document(doc, created_by="admin", mode="merge"))
    assert result["errors"] == [] or result["errors"] == 0, result["error_details"]
    assert (result["nodes"], result["edges"]) == (len(doc["nodes"]), len(doc["edges"]))
    assert result["graph_created"] is True


def test_find_seeds_lists_every_seed_with_its_graph_id():
    seeds = {s["id"]: s for s in seed_data.find_seeds()}
    assert {"hello-world", "eden"} <= set(seeds)
    assert seeds["eden"]["nodes"] == 9 and seeds["eden"]["edges"] == 8
    assert seeds["hello-world"]["path"].name == "hgai-hypergraph-hello-world.export.yml"


def test_resolve_seeds_by_id_by_path_and_default():
    assert {s["id"] for s in seed_data.resolve_seeds([])} >= {"hello-world", "eden"}
    assert [s["id"] for s in seed_data.resolve_seeds(["eden"])] == ["eden"]
    by_path = seed_data.resolve_seeds([str(SEEDS / "hgai-hypergraph-hello-world.export.yml")])
    assert [s["id"] for s in by_path] == ["hello-world"]
    with pytest.raises(seed_data.SeedError, match="neither a seed id"):
        seed_data.resolve_seeds(["nope"])


def test_a_file_that_is_not_an_export_is_rejected(tmp_path):
    bad = tmp_path / "x.export.yml"
    bad.write_text("hello: world\n")
    with pytest.raises(seed_data.SeedError, match="hgai_export"):
        seed_data.describe_seed(bad)
    noid = tmp_path / "y.export.yml"
    noid.write_text(yaml.safe_dump({"hgai_export": "1.0", "graph": {}, "nodes": [], "edges": []}))
    with pytest.raises(seed_data.SeedError, match="no graph id"):
        seed_data.describe_seed(noid)


def test_seed_folder_is_copied_into_the_docker_image():
    """The Dockerfile copies all of scripts/, which is what puts scripts/seeds/ in the container."""
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "COPY scripts/ ./scripts/" in dockerfile
    dockerignore = ROOT / ".dockerignore"
    if dockerignore.exists():
        assert "scripts" not in dockerignore.read_text()


def test_default_server_follows_hgai_port(monkeypatch):
    monkeypatch.delenv("HGAI_PORT", raising=False)
    assert seed_data.default_server() == "http://localhost:8357"
    monkeypatch.setenv("HGAI_PORT", "8000")
    assert seed_data.default_server() == "http://localhost:8000"
