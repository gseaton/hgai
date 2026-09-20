"""Hypergraph export-file / import logic (hgai.core.transfer).

The storage-backed paths (paging every node/edge out, creating real
documents) are exercised live against MongoDB; here the engine is faked so the
file-format validation, YAML round-trip, conflict handling and per-item error
reporting are tested in isolation."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from hgai.core import transfer

ROOT = Path(__file__).resolve().parent.parent


def make_doc(**overrides):
    doc = {
        "hgai_export": "1.0",
        "graph": {"id": "src-graph", "label": "Source Graph", "description": "d", "type": "instantiated",
                  "tags": ["a"], "attributes": {"k": 1}, "node_count": 9, "edge_count": 9,
                  "system_created": "2026-01-01T00:00:00Z", "version": 4},
        "nodes": [
            {"id": "n1", "label": "One", "type": "Person", "hypergraph_id": "src-graph", "version": 3,
             "system_created": "2026-01-01T00:00:00Z", "created_by": "someone", "mutations": [{"x": 1}],
             "media": [{"media_id": "m1", "filename": "f.png", "content_type": "image/png"}],
             "default_media_id": "m1"},
            {"id": "n2", "label": "Two", "type": "Person"},
        ],
        "edges": [
            {"id": "e1", "relation": "knows", "flavor": "hub", "hyperkey": "abc",
             "members": [{"node_id": "n1", "seq": 0}, {"node_id": "n2", "seq": 1}]},
        ],
    }
    doc.update(overrides)
    return doc


def fake_engine(existing_graph=None, existing_nodes=(), existing_edges=(), duplicate_edge=False):
    return SimpleNamespace(
        get_hypergraph=AsyncMock(return_value=existing_graph),
        create_hypergraph=AsyncMock(),
        get_hypernode=AsyncMock(side_effect=lambda g, nid, space_id=None: object() if nid in existing_nodes else None),
        create_hypernode=AsyncMock(),
        get_hyperedge=AsyncMock(side_effect=lambda g, eid, space_id=None: object() if eid in existing_edges else None),
        find_duplicate_hyperedge=AsyncMock(return_value=object() if duplicate_edge else None),
        create_hyperedge=AsyncMock(),
    )


def run_import(doc, engine_fake, **kwargs):
    kwargs.setdefault("created_by", "tester")
    with patch.object(transfer, "engine", engine_fake):
        return asyncio.run(transfer.import_document(transfer.validate_export(doc), **kwargs))


# ── file name / format ──

def test_export_filename_has_id_and_utc_timestamp():
    when = datetime(2026, 9, 20, 13, 5, 9, tzinfo=timezone.utc)
    assert transfer.export_filename("eden", when) == "hgai-hypergraph-eden-20260920130509.export.yml"
    assert transfer.export_filename("we ird/id!", when) == "hgai-hypergraph-we-ird-id-20260920130509.export.yml"
    assert transfer.export_filename("!!!", when).startswith("hgai-hypergraph-graph-")


def test_yaml_round_trip_preserves_the_document():
    doc = make_doc()
    text = transfer.dump_yaml(doc)
    assert text.startswith("hgai_export:")            # marker first, key order preserved
    assert transfer.parse_export(text) == transfer.validate_export(doc)


def test_parse_accepts_json_and_bytes_with_bom():
    doc = make_doc()
    assert transfer.parse_export(json.dumps(doc))["graph"]["id"] == "src-graph"
    assert transfer.parse_export(b"\xef\xbb\xbf" + yaml.safe_dump(doc).encode())["graph"]["id"] == "src-graph"


@pytest.mark.parametrize("raw, message", [
    ("just a string", "mapping"),
    ("nodes: []", "hgai_export"),
    ("hgai_export: '2.0'\nnodes: []", "Unsupported"),
    ("hgai_export: '1.0'\nnodes: 5", "list"),
    ("hgai_export: '1.0'\nedges: [1, 2]", "list of mappings"),
    ("hgai_export: '1.0'\ngraph: x", "'graph'"),
    ("a: [unclosed", "valid YAML"),
])
def test_invalid_files_are_rejected_with_a_readable_message(raw, message):
    with pytest.raises(transfer.ExportFormatError, match=message):
        transfer.parse_export(raw)


def test_non_utf8_is_rejected():
    with pytest.raises(transfer.ExportFormatError, match="UTF-8"):
        transfer.parse_export(b"\xff\xfe\x00bad")


def test_missing_nodes_and_edges_default_to_empty():
    doc = transfer.parse_export("hgai_export: '1.0'\ngraph: {id: g}")
    assert doc["nodes"] == [] and doc["edges"] == []


def test_the_repos_earlier_export_files_still_parse():
    """Files written by the pre-existing export endpoint must stay importable."""
    for name in ("hg-alpha.20260322.hgai.export.yaml", "freakshow-alpha.hg.export.yaml"):
        path = ROOT / name
        if path.exists():
            doc = transfer.parse_export(path.read_text())
            assert doc["nodes"] and doc["graph"]["id"]


# ── import ──

def test_create_mode_creates_the_graph_from_the_file_then_loads_items():
    eng = fake_engine()
    result = run_import(make_doc(), eng, space_id="team-a")

    graph_arg = eng.create_hypergraph.await_args.args[0]
    assert (graph_arg.id, graph_arg.label, graph_arg.space_id, graph_arg.tags) == ("src-graph", "Source Graph", "team-a", ["a"])
    assert graph_arg.attributes == {"k": 1} and graph_arg.description == "d"
    assert eng.create_hypergraph.await_args.kwargs["created_by"] == "tester"
    assert result["graph_created"] is True
    assert (result["nodes"], result["edges"], result["errors"]) == (2, 1, 0)
    # every item was created inside the target graph / space
    assert all(c.args[0] == "src-graph" and c.kwargs["space_id"] == "team-a" for c in eng.create_hypernode.await_args_list)


def test_graph_id_override_wins_over_the_files_id():
    eng = fake_engine()
    result = run_import(make_doc(), eng, graph_id="renamed")
    assert result["graph_id"] == "renamed"
    assert eng.create_hypergraph.await_args.args[0].id == "renamed"
    assert eng.create_hypernode.await_args_list[0].args[0] == "renamed"


def test_server_managed_fields_and_media_are_not_imported():
    eng = fake_engine()
    result = run_import(make_doc(), eng)
    node = eng.create_hypernode.await_args_list[0].args[1]
    assert node.media == [] and node.default_media_id is None
    assert node.created_by is None and node.version == 1   # HypernodeCreate defaults, not the file's values
    edge = eng.create_hyperedge.await_args_list[0].args[1]
    assert edge.id == "e1" and [m.node_id for m in edge.members] == ["n1", "n2"]
    assert result["media_references_dropped"] == 1


def test_create_mode_refuses_an_existing_graph_and_writes_nothing():
    eng = fake_engine(existing_graph=object())
    with pytest.raises(transfer.GraphExistsError):
        run_import(make_doc(), eng)
    eng.create_hypernode.assert_not_awaited()


def test_merge_mode_skips_what_is_already_there():
    eng = fake_engine(existing_graph=object(), existing_nodes={"n1"}, existing_edges={"e1"})
    result = run_import(make_doc(), eng, mode="merge")
    assert result["graph_created"] is False
    eng.create_hypergraph.assert_not_awaited()
    assert (result["nodes"], result["skipped_nodes"]) == (1, 1)
    assert (result["edges"], result["skipped_edges"]) == (0, 1)


def test_an_edge_with_the_same_identity_but_a_different_id_is_a_duplicate():
    eng = fake_engine(existing_graph=object(), duplicate_edge=True)
    result = run_import(make_doc(), eng, mode="merge")
    assert (result["edges"], result["skipped_edges"]) == (0, 1)


def test_merge_creates_a_missing_graph():
    eng = fake_engine()
    result = run_import(make_doc(), eng, mode="merge")
    assert result["graph_created"] is True


def test_require_existing_graph():
    with pytest.raises(transfer.GraphNotFoundError):
        run_import(make_doc(), fake_engine(), mode="merge", require_existing_graph=True)


def test_a_bad_item_is_reported_but_does_not_stop_the_rest():
    doc = make_doc()
    doc["nodes"].insert(0, {"label": "no id"})                       # invalid node
    doc["edges"].append({"id": "bad", "relation": "r", "members": "oops"})  # invalid edge
    eng = fake_engine()
    result = run_import(doc, eng)
    assert (result["nodes"], result["edges"], result["errors"]) == (2, 1, 2)
    assert any(d.startswith("node ") for d in result["error_details"])
    assert any(d.startswith("edge 'bad'") for d in result["error_details"])


def test_error_details_are_capped():
    doc = make_doc(nodes=[{"label": f"bad{i}"} for i in range(transfer.MAX_ERROR_DETAILS + 10)], edges=[])
    result = run_import(doc, fake_engine())
    assert result["errors"] == transfer.MAX_ERROR_DETAILS + 10
    assert len(result["error_details"]) == transfer.MAX_ERROR_DETAILS


def test_no_graph_id_anywhere_is_an_error():
    doc = make_doc(graph={})
    with pytest.raises(transfer.ExportFormatError, match="graph id"):
        run_import(doc, fake_engine())


def test_invalid_graph_definition_is_reported():
    doc = make_doc(graph={"id": "has.dot", "label": "x"})
    with pytest.raises(transfer.ExportFormatError, match="hypergraph definition"):
        run_import(doc, fake_engine())


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        run_import(make_doc(), fake_engine(), mode="overwrite")
