"""HTTP glue shared by the hypergraph and space routers for exporting a
hypergraph to a file and importing one (see hgai.core.transfer)."""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import Response

from hgai.core import transfer

MAX_IMPORT_BYTES = 100 * 1024 * 1024  # 100 MB of export text


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


async def run_import(
    doc: Dict[str, Any], created_by: str, graph_id: Optional[str],
    space_id: Optional[str], mode: str, require_existing_graph: bool = False,
) -> Dict[str, Any]:
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
