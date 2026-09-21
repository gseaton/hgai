"""Parameterized query (prepared statement) engine: CRUD + execution.

A ParameterizedQuery is a first-class resource (see
hgai.models.parameterized_query) — not a hypergraph entity — so this
module, not hgai.core.engine, owns its lifecycle. Follows the same
mutations-audit-trail convention hypernodes/hyperedges/notes use, via the
shared hgai.core.mutations helpers.

`parameters` is never set directly by a caller — it's recomputed from
`shql` on every create/update via hgai.core.query_templates.parse_parameters,
so it can never drift out of sync with the actual placeholders in the text.
"""

import uuid
from typing import List, Optional, Tuple

from hgai.core.mutations import append_mutation as _append_mutation
from hgai.core.mutations import create_delta as _create_delta
from hgai.core.mutations import update_delta as _update_delta
from hgai.core.query_templates import parse_parameters, render_query
from hgai.db.storage import get_storage
from hgai.models.common import now_utc
from hgai.models.parameterized_query import (
    ParameterizedQueryCreate,
    ParameterizedQueryInDB,
    ParameterizedQueryUpdate,
)
from hgai_module_storage.filters import ParameterizedQueryFilters, ParameterizedQueryPatch

TRACKED_FIELDS = ["name", "label", "description", "shql", "tags", "status", "attributes"]


async def create_parameterized_query(data: ParameterizedQueryCreate, created_by: str) -> ParameterizedQueryInDB:
    parameters = [p.model_dump() for p in parse_parameters(data.shql)]

    now = now_utc()
    doc = data.model_dump()
    create_delta = _create_delta(doc, TRACKED_FIELDS)
    doc.update(
        id=uuid.uuid4().hex,
        parameters=parameters,
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
        mutations=_append_mutation([], "create", create_delta, created_by),
    )
    return await get_storage().parameterized_queries.create(doc)


async def get_parameterized_query(query_id: str) -> Optional[ParameterizedQueryInDB]:
    return await get_storage().parameterized_queries.get(query_id)


async def list_parameterized_queries(
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    sort: Optional[List[Tuple[str, int]]] = None,
) -> Tuple[int, List[ParameterizedQueryInDB]]:
    filters = ParameterizedQueryFilters(tags=tags, search=search, sort=sort)
    return await get_storage().parameterized_queries.list(filters, skip=skip, limit=limit)


async def update_parameterized_query(
    query_id: str, data: ParameterizedQueryUpdate, updated_by: str
) -> Optional[ParameterizedQueryInDB]:
    existing = await get_parameterized_query(query_id)
    if not existing:
        return None

    dumped = data.model_dump(exclude_none=True)
    existing_dump = existing.model_dump()
    existing_mutations = existing_dump.get("mutations", [])
    update_delta = _update_delta(existing_dump, dumped, TRACKED_FIELDS)
    new_mutations = _append_mutation(existing_mutations, "mutate", update_delta, updated_by)

    # Re-derive `parameters` whenever `shql` changes, so it never drifts out
    # of sync with the text actually stored.
    parameters = None
    if "shql" in dumped:
        parameters = [p.model_dump() for p in parse_parameters(dumped["shql"])]

    patch = ParameterizedQueryPatch(
        name=dumped.get("name"),
        label=dumped.get("label"),
        description=dumped.get("description"),
        shql=dumped.get("shql"),
        parameters=parameters,
        tags=dumped.get("tags"),
        attributes=dumped.get("attributes"),
        status=dumped.get("status"),
        mutations=new_mutations if new_mutations is not existing_mutations else None,
    )
    return await get_storage().parameterized_queries.update(query_id, patch)


async def delete_parameterized_query(query_id: str) -> bool:
    return await get_storage().parameterized_queries.delete(query_id)


async def execute_parameterized_query(query_id: str, values: dict, use_cache: bool = True, *, account):
    """Render `query_id`'s template with `values` and run it through SHQL.

    Raises `QueryTemplateError` (from hgai.core.query_templates) if `values`
    doesn't satisfy the template's declared parameters — the caller (the API
    router) is expected to turn that into a 400, same as an SHQL parse error
    already does for a malformed literal query. The rendered query runs with
    `account`'s graph permissions (SHQLPermissionError -> 403 in the router).
    """
    from hgai_module_shql.engine import execute_shql

    query = await get_parameterized_query(query_id)
    if not query:
        return None, None
    rendered = render_query(query.shql, values)
    result = await execute_shql(rendered, use_cache=use_cache, account=account)
    return rendered, result
