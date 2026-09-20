"""Hypergraph export files and import.

An export file (`hgai-hypergraph-<graph-id>-<YYYYMMDDHHMMSS>.export.yml`) is a
YAML document — JSON is accepted too, being a YAML subset — with this shape:

    hgai_export: '1.0'
    exported_at: <iso datetime>
    source: {server_id, server_name}
    counts: {nodes, edges}
    graph: {id, label, type, tags, attributes, ...}
    nodes: [ {id, label, type, attributes, ...}, ... ]
    edges: [ {id, relation, members, flavor, ...}, ... ]

`engine.export_hypergraph` builds the document; `import_document` loads one
into this instance, creating the hypergraph from its `graph` block when it
doesn't exist yet. Server-managed fields (timestamps, version, audit trail,
hyperkey, created_by) are never trusted from a file — the importing instance
regenerates them — and media *references* are dropped, since the media files
themselves are not part of an export and would dangle on another instance.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import ValidationError

from hgai.core import engine
from hgai.models.hyperedge import HyperedgeCreate
from hgai.models.hypergraph import HypergraphCreate
from hgai.models.hypernode import HypernodeCreate

SUPPORTED_MAJOR_VERSION = "1"
IMPORT_MODES = ("create", "merge")
MAX_ERROR_DETAILS = 25

_GRAPH_METADATA_FIELDS = ("label", "description", "type", "composition", "remote_refs", "tags", "status", "attributes")
_SERVER_MANAGED = ("hypergraph_id", "system_created", "system_updated", "created_by", "version", "mutations")


class ExportFormatError(ValueError):
    """The uploaded text isn't a usable HypergraphAI export file."""


class GraphExistsError(Exception):
    """mode='create' but the target hypergraph already exists."""


class GraphNotFoundError(Exception):
    """The target hypergraph must already exist but doesn't."""


# ─── Export helpers ───────────────────────────────────────────────────────────

def export_filename(graph_id: str, now: Optional[datetime] = None) -> str:
    """`hgai-hypergraph-<graph-id>-<YYYYMMDDHHMMSS>.export.yml` (UTC timestamp)."""
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d%H%M%S")
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", graph_id).strip("-") or "graph"
    return f"hgai-hypergraph-{safe_id}-{stamp}.export.yml"


def dump_yaml(document: Dict[str, Any]) -> str:
    """Serialize an export document (already JSON-safe — see engine.export_hypergraph)."""
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True, default_flow_style=False)


# ─── Parsing / validation ─────────────────────────────────────────────────────

def validate_export(doc: Any) -> Dict[str, Any]:
    """Check an already-parsed document and normalize `graph`/`nodes`/`edges`
    to a dict / two lists of dicts. Raises ExportFormatError with a message
    meant to be shown to the user."""
    if not isinstance(doc, dict):
        raise ExportFormatError("The file does not contain a YAML/JSON mapping")
    version = str(doc.get("hgai_export") or "").strip()
    if not version:
        raise ExportFormatError("Missing the 'hgai_export' marker — this is not a HypergraphAI export file")
    if version.split(".")[0] != SUPPORTED_MAJOR_VERSION:
        raise ExportFormatError(
            f"Unsupported export format version '{version}' (this server reads {SUPPORTED_MAJOR_VERSION}.x)"
        )

    graph = doc.get("graph") or {}
    if not isinstance(graph, dict):
        raise ExportFormatError("'graph' must be a mapping")
    normalized: Dict[str, Any] = dict(doc, graph=graph)
    for key in ("nodes", "edges"):
        items = doc.get(key) or []
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise ExportFormatError(f"'{key}' must be a list of mappings")
        normalized[key] = items
    return normalized


def parse_export(raw: Union[str, bytes]) -> Dict[str, Any]:
    """Parse and validate the text of an export file (YAML or JSON)."""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ExportFormatError("The file is not UTF-8 text")
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ExportFormatError(f"The file is not valid YAML/JSON: {e}")
    return validate_export(doc)


# ─── Import ───────────────────────────────────────────────────────────────────

def _first_line(exc: Exception) -> str:
    text = str(exc).strip().splitlines()
    return text[0] if text else exc.__class__.__name__


async def import_document(
    doc: Dict[str, Any],
    created_by: str,
    graph_id: Optional[str] = None,
    space_id: Optional[str] = None,
    mode: str = "create",
    require_existing_graph: bool = False,
) -> Dict[str, Any]:
    """Load a validated export document into this instance.

    graph_id      target id; defaults to the id in the file's `graph` block.
    space_id      space that owns (or will own) the target graph; None = unowned.
    mode          'create' — the hypergraph must not exist yet (else GraphExistsError);
                  'merge'  — load into it if it exists, otherwise create it. Nodes and
                  edges that are already present (same id, or the same edge identity)
                  are skipped rather than overwritten.
    require_existing_graph  never create the hypergraph (GraphNotFoundError instead).

    Returns counts plus up to MAX_ERROR_DETAILS error messages. One bad item
    never aborts the import — it is counted under `errors` and the rest load.
    """
    if mode not in IMPORT_MODES:
        raise ValueError(f"mode must be one of {IMPORT_MODES}")
    graph_meta = doc.get("graph") or {}
    target = graph_id or graph_meta.get("id")
    if not target:
        raise ExportFormatError("The file has no graph id — supply one explicitly")

    existing = await engine.get_hypergraph(target, space_id=space_id)
    graph_created = False
    if existing:
        if mode == "create":
            raise GraphExistsError(target)
    else:
        if require_existing_graph:
            raise GraphNotFoundError(target)
        fields = {k: graph_meta[k] for k in _GRAPH_METADATA_FIELDS if graph_meta.get(k) is not None}
        try:
            create = HypergraphCreate(id=target, space_id=space_id, **dict(fields, label=fields.get("label") or target))
        except ValidationError as e:
            raise ExportFormatError(f"Invalid hypergraph definition: {_first_line(e)}")
        await engine.create_hypergraph(create, created_by=created_by)
        graph_created = True

    result: Dict[str, Any] = {
        "graph_id": target, "space_id": space_id, "graph_created": graph_created,
        "nodes": 0, "edges": 0, "skipped_nodes": 0, "skipped_edges": 0,
        "errors": 0, "error_details": [], "media_references_dropped": 0,
    }

    def fail(kind: str, item_id: Any, exc: Exception) -> None:
        result["errors"] += 1
        if len(result["error_details"]) < MAX_ERROR_DETAILS:
            result["error_details"].append(f"{kind} '{item_id}': {_first_line(exc)}")

    def clean(item: Dict[str, Any], extra_drop: tuple = ()) -> Dict[str, Any]:
        result["media_references_dropped"] += len(item.get("media") or [])
        drop = _SERVER_MANAGED + ("media", "default_media_id") + extra_drop
        return {k: v for k, v in item.items() if k not in drop}

    for raw in doc["nodes"]:
        node_id = raw.get("id")
        try:
            node = HypernodeCreate(**clean(raw))
            if await engine.get_hypernode(target, node.id, space_id=space_id):
                result["skipped_nodes"] += 1
                continue
            await engine.create_hypernode(target, node, created_by, space_id=space_id)
            result["nodes"] += 1
        except Exception as e:  # noqa: BLE001 — reported per item, never aborts the import
            fail("node", node_id, e)

    for raw in doc["edges"]:
        edge_id = raw.get("id")
        try:
            edge = HyperedgeCreate(**clean(raw, ("hyperkey",)))
            already = bool(edge.id and await engine.get_hyperedge(target, edge.id, space_id=space_id))
            if not already:
                already = bool(await engine.find_duplicate_hyperedge(
                    target, edge.relation, [m.node_id for m in edge.members],
                    edge.valid_from, edge.valid_to, space_id=space_id,
                ))
            if already:
                result["skipped_edges"] += 1
                continue
            await engine.create_hyperedge(target, edge, created_by, space_id=space_id)
            result["edges"] += 1
        except Exception as e:  # noqa: BLE001
            fail("edge", edge_id, e)

    return result
