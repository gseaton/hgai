"""HTTP glue shared by the hypergraph and space routers for exporting a
hypergraph to a file and importing one (see hgai.core.transfer)."""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import Response

from hgai.core import rdf_import, transfer

MAX_IMPORT_BYTES = 100 * 1024 * 1024  # 100 MB of export text


def _local_attribute_name(key: str) -> str:
    """The part of an attribute key after its last '#' or '/' (whichever
    comes later), or after its last ':' if it has neither — 'ex:sex' ->
    'sex', 'http://example.org/description' -> 'description'. '#'/'/' win
    over ':' so a full IRI (which also contains a ':' from its scheme,
    e.g. 'http:') splits on its last path segment or fragment, not on
    'http'. A key ending in its own only usable separator (nothing follows
    it), or with none of these separators at all, is returned unchanged."""
    idx = max(key.rfind("#"), key.rfind("/"))
    if idx != -1:
        return key[idx + 1:] if idx + 1 < len(key) else key
    idx = key.rfind(":")
    if idx != -1 and idx + 1 < len(key):
        return key[idx + 1:]
    return key


def _strip_attribute_key_prefixes(attributes: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Rewrite each attribute key to its local name, for the 'Suppress
    Attribute Prefixes' import option. A key is left untouched if its local
    name is unchanged, or if that local name is shared with another key in
    the same attributes document (either another key's own local name, or
    an already-unprefixed key) — silently merging two different attributes
    into one would be a worse outcome than leaving a prefix in place."""
    if not attributes:
        return attributes
    local_names = {k: _local_attribute_name(k) for k in attributes}
    counts: Dict[str, int] = {}
    for local in local_names.values():
        counts[local] = counts.get(local, 0) + 1
    return {
        (local_names[k] if local_names[k] != k and counts[local_names[k]] == 1 else k): v
        for k, v in attributes.items()
    }


def strip_attribute_prefixes_in_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Applies `_strip_attribute_key_prefixes` to every node's and edge's
    `attributes` document in an in-memory export document (the shape both a
    native export file and `rdf_to_export_document` produce)."""
    for collection in ("nodes", "edges"):
        for item in doc.get(collection) or []:
            attrs = item.get("attributes")
            if attrs:
                item["attributes"] = _strip_attribute_key_prefixes(attrs)
    return doc


def export_response(data: Dict[str, Any], graph_id: str, fmt: str):
    """`json` returns the document as ordinary JSON; `yaml` returns it as a
    downloadable `hgai-hypergraph-<id>-<timestamp>.export.yml` attachment."""
    if fmt != "yaml":
        return data
    filename = transfer.export_filename(graph_id)
    return Response(
        content=transfer.dump_yaml(data),
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


async def read_export_body(request: Request) -> Dict[str, Any]:
    """The request body is the raw text of an export file (YAML or JSON)."""
    body = await request.body()
    if len(body) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail=f"Export file exceeds the {MAX_IMPORT_BYTES // (1024 * 1024)} MB limit")
    if not body.strip():
        raise HTTPException(status_code=400, detail="The request body is empty — send the export file's text")
    try:
        return transfer.parse_export(body)
    except transfer.ExportFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def read_rdf_body(
    request: Request, graph_id: str, fmt: Optional[str], label: Optional[str],
) -> Dict[str, Any]:
    """The request body is the raw text of an RDF file (Turtle, RDF/XML,
    JSON-LD or Notation3); converted to the same in-memory shape as a native
    export document so it can go through the same `run_import` as one."""
    body = await request.body()
    if len(body) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail=f"RDF file exceeds the {MAX_IMPORT_BYTES // (1024 * 1024)} MB limit")
    if not body.strip():
        raise HTTPException(status_code=400, detail="The request body is empty — send the RDF file's text")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="The file is not UTF-8 text")
    try:
        resolved = rdf_import.resolve_format(fmt)
        return rdf_import.rdf_to_export_document(text, resolved, graph_id, label=label)
    except rdf_import.RdfFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def run_import(
    doc: Dict[str, Any], created_by: str, graph_id: Optional[str],
    space_id: Optional[str], mode: str, require_existing_graph: bool = False,
    strip_attribute_prefixes: bool = False,
) -> Dict[str, Any]:
    if strip_attribute_prefixes:
        doc = strip_attribute_prefixes_in_doc(doc)
    try:
        return await transfer.import_document(
            doc, created_by=created_by, graph_id=graph_id, space_id=space_id,
            mode=mode, require_existing_graph=require_existing_graph,
        )
    except transfer.ExportFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except transfer.GraphExistsError as e:
        where = f" in space '{space_id}'" if space_id else ""
        raise HTTPException(
            status_code=409,
            detail=f"Hypergraph '{e}' already exists{where} — choose another id, or import with mode=merge",
        )
    except transfer.GraphNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{e}' not found")
