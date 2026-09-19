"""AI Agent REST endpoints: vendor/model CRUD (Phase 1), chat
sessions/messages (Phase 2), Note export (Phase 3), and per-account prompt
history.

Vendors are admin-only end to end (they hold encrypted API keys — same
gating as Meshes). Models are admin-only to write, but readable by any
authenticated account so the chat panel's model picker can list them.

Chat sessions/messages are owner-only (like Notes) — any authenticated
account can create and use its own sessions against whichever models an
admin has enabled, but can never see another account's conversations
(admins can, same override every other owner-only resource already has).
Prompt history is likewise per-account and server-side (see
hgai_module_agentchat/prompt_history.py) — same pattern as
hgai_module_shql's query history.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from hgai.api.deps import get_current_active_account
from hgai.core.auth import require_admin
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.note import NoteResponse

from . import engine, notes_export, store
from .models import (
    AgentChatMessageResponse,
    AgentChatSendRequest,
    AgentChatSessionCreate,
    AgentChatSessionInDB,
    AgentChatSessionResponse,
    AgentChatSessionUpdate,
    AgentModelCreate,
    AgentModelInDB,
    AgentModelResponse,
    AgentModelUpdate,
    AgentVendorCreate,
    AgentVendorInDB,
    AgentVendorResponse,
    AgentVendorUpdate,
)

router = APIRouter(prefix="/agent", tags=["agent"])


# ─── Vendors (admin-only) ───────────────────────────────────────────────────

@router.get("/vendors", response_model=PaginatedResponse)
async def list_vendors_route(
    tags: Optional[List[str]] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Substring match against name, label, or base_url"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _admin: AccountInDB = Depends(require_admin),
):
    total, items = await store.list_vendors(tags=tags, search=search, skip=skip, limit=limit)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[v.model_dump() for v in items])


@router.post("/vendors", response_model=AgentVendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor_route(data: AgentVendorCreate, admin: AccountInDB = Depends(require_admin)):
    return await store.create_vendor(data, admin.username)


@router.get("/vendors/{vendor_id}", response_model=AgentVendorResponse)
async def get_vendor_route(vendor_id: str, _admin: AccountInDB = Depends(require_admin)):
    vendor = await store.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Agent vendor '{vendor_id}' not found")
    return vendor


@router.put("/vendors/{vendor_id}", response_model=AgentVendorResponse)
async def update_vendor_route(vendor_id: str, data: AgentVendorUpdate, admin: AccountInDB = Depends(require_admin)):
    result = await store.update_vendor(vendor_id, data, admin.username)
    if not result:
        raise HTTPException(status_code=404, detail=f"Agent vendor '{vendor_id}' not found")
    return result


@router.delete("/vendors/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor_route(vendor_id: str, _admin: AccountInDB = Depends(require_admin)):
    deleted = await store.delete_vendor(vendor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent vendor '{vendor_id}' not found")


# ─── Models (read: any account; write: admin) ───────────────────────────────

@router.get("/models", response_model=PaginatedResponse)
async def list_models_route(
    vendor_id: Optional[str] = Query(default=None),
    tags: Optional[List[str]] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Substring match against model_id, label, or description"),
    enabled_only: bool = Query(default=False, description="Only return enabled models — used by the chat panel's model picker"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _account: AccountInDB = Depends(get_current_active_account),
):
    total, items = await store.list_models(
        vendor_id=vendor_id, tags=tags, search=search, enabled_only=enabled_only, skip=skip, limit=limit,
    )
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[m.model_dump() for m in items])


@router.post("/models", response_model=AgentModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model_route(data: AgentModelCreate, admin: AccountInDB = Depends(require_admin)):
    vendor = await store.get_vendor(data.vendor_id)
    if not vendor:
        raise HTTPException(status_code=400, detail=f"Agent vendor '{data.vendor_id}' not found")
    return await store.create_model(data, admin.username)


@router.get("/models/{model_id}", response_model=AgentModelResponse)
async def get_model_route(model_id: str, _account: AccountInDB = Depends(get_current_active_account)):
    model = await store.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Agent model '{model_id}' not found")
    return model


@router.put("/models/{model_id}", response_model=AgentModelResponse)
async def update_model_route(model_id: str, data: AgentModelUpdate, admin: AccountInDB = Depends(require_admin)):
    result = await store.update_model(model_id, data, admin.username)
    if not result:
        raise HTTPException(status_code=404, detail=f"Agent model '{model_id}' not found")
    return result


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_route(model_id: str, _admin: AccountInDB = Depends(require_admin)):
    deleted = await store.delete_model(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent model '{model_id}' not found")


# ─── Chat sessions/messages (owner-only) ────────────────────────────────────

async def _get_owned_session(session_id: str, account: AccountInDB) -> AgentChatSessionInDB:
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session '{session_id}' not found")
    if session.owner_username != account.username and "admin" not in account.roles:
        raise HTTPException(status_code=403, detail="Not permitted to access this chat session")
    return session


async def _resolve_usable_model(session: AgentChatSessionInDB) -> tuple[AgentModelInDB, AgentVendorInDB]:
    model = await store.get_model(session.model_id)
    if not model or not model.enabled:
        raise HTTPException(status_code=400, detail="This session's model is not available (missing or disabled)")
    vendor = await store.get_vendor(model.vendor_id)
    if not vendor or not vendor.enabled:
        raise HTTPException(status_code=400, detail="This session's vendor is not available (missing or disabled)")
    return model, vendor


@router.get("/sessions", response_model=PaginatedResponse)
async def list_sessions_route(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    account: AccountInDB = Depends(get_current_active_account),
):
    total, items = await store.list_sessions(account.username, skip=skip, limit=limit)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[s.model_dump() for s in items])


@router.post("/sessions", response_model=AgentChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session_route(data: AgentChatSessionCreate, account: AccountInDB = Depends(get_current_active_account)):
    model = await store.get_model(data.model_id)
    if not model:
        raise HTTPException(status_code=400, detail=f"Agent model '{data.model_id}' not found")
    return await store.create_session(data, account.username)


@router.get("/sessions/{session_id}", response_model=AgentChatSessionResponse)
async def get_session_route(session_id: str, account: AccountInDB = Depends(get_current_active_account)):
    return await _get_owned_session(session_id, account)


@router.put("/sessions/{session_id}", response_model=AgentChatSessionResponse)
async def update_session_route(
    session_id: str, data: AgentChatSessionUpdate, account: AccountInDB = Depends(get_current_active_account),
):
    await _get_owned_session(session_id, account)
    if data.title is not None:
        result = await store.update_session_title(session_id, data.title)
        if result:
            return result
    return await store.get_session(session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session_route(session_id: str, account: AccountInDB = Depends(get_current_active_account)):
    await _get_owned_session(session_id, account)
    await store.delete_session(session_id)


@router.get("/sessions/{session_id}/messages", response_model=List[AgentChatMessageResponse])
async def list_messages_route(session_id: str, account: AccountInDB = Depends(get_current_active_account)):
    await _get_owned_session(session_id, account)
    return await store.list_messages(session_id)


@router.post("/sessions/{session_id}/messages", response_model=AgentChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message_route(
    session_id: str, body: AgentChatSendRequest, account: AccountInDB = Depends(get_current_active_account),
):
    """Non-streaming: runs the full turn and returns the assistant's
    message once complete. See .../messages/stream for the SSE variant."""
    session = await _get_owned_session(session_id, account)
    model, vendor = await _resolve_usable_model(session)
    try:
        return await engine.run_turn(session, vendor, model, account, body.prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent run failed: {e}")


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream_route(
    session_id: str, body: AgentChatSendRequest, account: AccountInDB = Depends(get_current_active_account),
):
    """Streaming (SSE): `data:` frames carry `{"delta": "..."}` text chunks
    as they arrive, terminated by either `event: done` (with the persisted
    assistant message's id) or `event: error`."""
    session = await _get_owned_session(session_id, account)
    model, vendor = await _resolve_usable_model(session)
    return StreamingResponse(
        engine.run_turn_stream(session, vendor, model, account, body.prompt),
        media_type="text/event-stream",
    )


@router.post(
    "/sessions/{session_id}/messages/{message_id}/save-note",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_message_as_note_route(
    session_id: str, message_id: str, account: AccountInDB = Depends(get_current_active_account),
):
    """Export one assistant turn (its paired user prompt + the response) as
    a Note, with the source prompt, vendor/model, timing, and token usage
    recorded as YAML frontmatter — see hgai_module_agentchat/notes_export.py."""
    await _get_owned_session(session_id, account)
    try:
        return await notes_export.export_message_to_note(session_id, message_id, account)
    except notes_export.NoteExportError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Prompt history (per-account, server-side) ──────────────────────────────

class AgentPromptHistoryEntryRequest(BaseModel):
    prompt: str


@router.get("/prompt-history")
async def get_agent_prompt_history_route(account: AccountInDB = Depends(get_current_active_account)):
    """The caller's own last 50 submitted chat prompts, newest first.

    Per-account and server-side, so it follows the account across
    browsers/devices/machines and survives a server restart."""
    from .prompt_history import list_history
    return {"items": await list_history(account.username)}


@router.post("/prompt-history")
async def add_agent_prompt_history_entry_route(
    request: AgentPromptHistoryEntryRequest, account: AccountInDB = Depends(get_current_active_account),
):
    """Record one submitted prompt. Called by the UI right when a chat
    message is sent, independent of whether the turn succeeds — this is a
    history of what was *submitted*, not of what got a good answer."""
    from .prompt_history import add_history_entry
    return await add_history_entry(account.username, request.prompt)


@router.delete("/prompt-history")
async def clear_agent_prompt_history_route(account: AccountInDB = Depends(get_current_active_account)):
    """Delete all of the caller's own prompt history entries."""
    from .prompt_history import clear_history
    count = await clear_history(account.username)
    return {"deleted": count}
