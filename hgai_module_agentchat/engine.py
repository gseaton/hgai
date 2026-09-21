"""Agno-backed chat agent engine.

Builds a fresh per-turn `Agent` (the session's vendor/model, the resident
hgai MCP server's tools via HgaiMcpToolkit, web access via HgaiWebToolkit,
help-topic access via HgaiHelpToolkit, and Mongo-backed multi-turn
history), runs one turn, and records hgai's own
lightweight per-turn audit metadata (vendor/model/timing/tokens) via
hgai_module_agentchat.store.

Agno's own MongoDb-backed session store is the source of truth for
conversation replay — reusing `session.id` as Agno's `session_id` on every
call is the entire "session restart" mechanism; nothing here reconstructs
message history by hand. The AgentChatMessage records this module writes
are a separate, hgai-owned export/audit layer on top of it (used by session
listing and the Note-export feature), not a second copy of the same data.
"""

import time
from typing import Any, AsyncIterator, Optional

from agno.agent import Agent
from agno.db.mongo import MongoDb
from agno.run.agent import RunCompletedEvent, RunContentEvent, RunErrorEvent

from hgai.config import get_settings
from hgai.core.auth import create_access_token
from hgai.models.account import AccountInDB
from hgai.models.common import now_utc

from . import store
from .help_toolkit import HgaiHelpToolkit
from .mcp_toolkit import HgaiMcpToolkit
from .web_toolkit import HgaiWebToolkit
from .models import (
    AgentChatMessageInDB,
    AgentChatSessionInDB,
    AgentModelInDB,
    AgentVendorInDB,
    AgentVendorName,
)

_agno_db: Optional[MongoDb] = None

AGENT_INSTRUCTIONS = [
    "You are the HypergraphAI assistant, embedded in the HypergraphAI Web UI.",
    "For questions about HypergraphAI itself — what it is, hypernodes/hyperedges/hypergraphs, SHQL syntax, "
    "inferencing, configuration, the REST or MCP APIs, or how to use the Web UI — call help_search first, "
    "read the best matching topic with help_get, and answer from it. Mention the topic id(s) you relied on. "
    "If the help topics don't cover the question, say so instead of guessing.",
    "For questions about the knowledge stored in the user's hypergraphs, use the hgai_* tools. Answer from "
    "the data those tools return, and say when the data doesn't contain the answer.",
    "Use web_fetch only to read a specific URL the user gives you (or one found in the data).",
]


def _get_agno_db() -> MongoDb:
    """Agno's own session/run storage, pointed at the same MongoDB database
    hgai already uses (distinct, agentchat_-prefixed collection names) so
    there's one database to operate/back up, not two. Built lazily and
    cached — Agno's MongoDb uses a synchronous pymongo client internally,
    separate from hgai's own Motor connection lifecycle."""
    global _agno_db
    if _agno_db is None:
        settings = get_settings()
        _agno_db = MongoDb(
            db_url=settings.mongo_uri,
            db_name=settings.mongo_db,
            session_collection="agentchat_agno_sessions",
            runs_collection="agentchat_agno_runs",
            memory_collection="agentchat_agno_memory",
        )
    return _agno_db


def _build_model(vendor: AgentVendorInDB, model: AgentModelInDB, api_key: str) -> Any:
    kwargs: dict = {"id": model.model_id, "api_key": api_key}
    if model.default_temperature is not None:
        kwargs["temperature"] = model.default_temperature
    if model.default_max_tokens is not None:
        kwargs["max_tokens"] = model.default_max_tokens

    if vendor.name == AgentVendorName.anthropic:
        from agno.models.anthropic import Claude
        return Claude(**kwargs)
    if vendor.name == AgentVendorName.openai:
        from agno.models.openai import OpenAIChat
        if vendor.base_url:
            kwargs["base_url"] = vendor.base_url
        return OpenAIChat(**kwargs)
    if vendor.name == AgentVendorName.xai:
        from agno.models.xai import xAI
        if vendor.base_url:
            kwargs["base_url"] = vendor.base_url
        return xAI(**kwargs)
    raise ValueError(f"Vendor kind '{vendor.name}' is not wired into the chat engine yet")


async def build_agent(vendor: AgentVendorInDB, model: AgentModelInDB, account: AccountInDB) -> Agent:
    """Construct a fresh per-turn Agent. A new JWT + MCP toolkit connection
    is minted for every call rather than cached/reused across turns — the
    handshake is cheap (one local HTTP round-trip). The MCP server authorizes
    each tool call against the account this JWT names, so the agent can only
    reach what the signed-in user may — never mint this token for anyone else."""
    api_key = await store.get_decrypted_api_key(vendor.id)
    if not api_key:
        raise ValueError(f"Vendor '{vendor.label}' has no API key configured")

    token, _ = create_access_token(account.username, account.roles)
    mcp_toolkit = await HgaiMcpToolkit.connect(bearer_token=token)

    return Agent(
        model=_build_model(vendor, model, api_key),
        db=_get_agno_db(),
        tools=[mcp_toolkit, HgaiWebToolkit(), HgaiHelpToolkit(account.username)],
        instructions=AGENT_INSTRUCTIONS,
        add_history_to_context=True,
        num_history_runs=10,
        markdown=True,
    )


def _metrics_fields(metrics: Any) -> dict:
    if metrics is None:
        return {"tokens_input": None, "tokens_output": None, "tokens_total": None}
    return {
        "tokens_input": getattr(metrics, "input_tokens", None),
        "tokens_output": getattr(metrics, "output_tokens", None),
        "tokens_total": getattr(metrics, "total_tokens", None),
    }


async def run_turn(
    session: AgentChatSessionInDB,
    vendor: AgentVendorInDB,
    model: AgentModelInDB,
    account: AccountInDB,
    prompt: str,
) -> AgentChatMessageInDB:
    """Run one non-streaming turn and persist the user+assistant audit
    record pair. Returns the assistant's AgentChatMessage."""
    agent = await build_agent(vendor, model, account)

    started_at = now_utc()
    t0 = time.monotonic()
    run = await agent.arun(input=prompt, session_id=session.id, user_id=account.username)
    duration_ms = int((time.monotonic() - t0) * 1000)
    ended_at = now_utc()

    await store.create_message(
        session_id=session.id, role="user", content=prompt,
        vendor_name=vendor.name, model_id=model.model_id,
        started_at=started_at, ended_at=started_at, duration_ms=0,
    )
    assistant_message = await store.create_message(
        session_id=session.id, role="assistant", content=run.content or "",
        vendor_name=vendor.name, model_id=model.model_id,
        started_at=started_at, ended_at=ended_at, duration_ms=duration_ms,
        **_metrics_fields(getattr(run, "metrics", None)),
    )
    await store.touch_session(session.id)
    return assistant_message


async def run_turn_stream(
    session: AgentChatSessionInDB,
    vendor: AgentVendorInDB,
    model: AgentModelInDB,
    account: AccountInDB,
    prompt: str,
) -> AsyncIterator[str]:
    """Run one streaming turn, yielding pre-formatted SSE frames. Text
    deltas stream as they arrive; the final frame is either `event: done`
    (carrying the persisted assistant message's id) or `event: error`. The
    user+assistant audit record pair is persisted once streaming completes,
    from the run's own RunCompletedEvent (not from re-assembling deltas) so
    the stored content always matches exactly what the model actually
    returned as final."""
    import json as _json

    agent = await build_agent(vendor, model, account)

    started_at = now_utc()
    t0 = time.monotonic()
    final_content: Optional[str] = None
    final_metrics: Any = None
    error: Optional[str] = None

    try:
        async for event in agent.arun(
            input=prompt, session_id=session.id, user_id=account.username,
            stream=True, stream_events=True,
        ):
            if isinstance(event, RunContentEvent) and event.content:
                yield f"data: {_json.dumps({'delta': event.content})}\n\n"
            elif isinstance(event, RunCompletedEvent):
                final_content = event.content
                final_metrics = getattr(event, "metrics", None)
            elif isinstance(event, RunErrorEvent):
                error = str(getattr(event, "content", None) or "Agent run failed")
    except Exception as e:  # noqa: BLE001 — surfaced to the client as an SSE error frame, not swallowed
        error = str(e)

    if error:
        yield f"event: error\ndata: {_json.dumps({'error': error})}\n\n"
        return

    duration_ms = int((time.monotonic() - t0) * 1000)
    ended_at = now_utc()

    await store.create_message(
        session_id=session.id, role="user", content=prompt,
        vendor_name=vendor.name, model_id=model.model_id,
        started_at=started_at, ended_at=started_at, duration_ms=0,
    )
    assistant_message = await store.create_message(
        session_id=session.id, role="assistant", content=final_content or "",
        vendor_name=vendor.name, model_id=model.model_id,
        started_at=started_at, ended_at=ended_at, duration_ms=duration_ms,
        **_metrics_fields(final_metrics),
    )
    await store.touch_session(session.id)
    yield f"event: done\ndata: {_json.dumps({'message_id': assistant_message.id})}\n\n"
