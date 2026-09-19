"""Lightweight MCP streamable-HTTP client + Agno Toolkit wrapper for the
resident hgai MCP server (see hgai_module_mcp).

Deliberately does NOT use `agno.tools.mcp.MCPTools` or the `mcp` PyPI
package on the client side: Agno's `mcp` extra pins `mcp>=2.1.0`, which
conflicts with this project's own `mcp==1.30.0` (hgai_module_mcp imports
`mcp.server.*` internals directly, and a major-version bump there is exactly
the kind of change that already broke this server once this same session).
This speaks the same streamable-HTTP JSON-RPC protocol directly over
`httpx` instead — validated end-to-end against the live server during the
Phase-0 spike (a real Agno Agent successfully called `hgai_query_execute`
through it).
"""

import json
import uuid
from typing import Any, Dict, List, Optional

import httpx

from agno.tools import Toolkit
from agno.tools.function import Function

from hgai.config import get_settings


class HgaiMcpClient:
    """Minimal MCP streamable-HTTP JSON-RPC client for one authenticated
    session against the resident server."""

    def __init__(self, url: str, bearer_token: str):
        self.url = url
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        self.session_id: Optional[str] = None
        self._client = httpx.AsyncClient(timeout=60)

    def _parse_sse_or_json(self, resp: httpx.Response) -> Dict[str, Any]:
        ctype = resp.headers.get("content-type", "")
        if "text/event-stream" in ctype:
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[len("data:"):].strip())
            raise RuntimeError(f"No data: line in SSE body: {resp.text!r}")
        return resp.json()

    async def _call(self, method: str, params: Optional[dict] = None, notification: bool = False):
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notification:
            payload["id"] = str(uuid.uuid4())
        resp = await self._client.post(self.url, headers=headers, json=payload)
        if "mcp-session-id" in resp.headers:
            self.session_id = resp.headers["mcp-session-id"]
        if notification:
            return None
        resp.raise_for_status()
        data = self._parse_sse_or_json(resp)
        if "error" in data:
            raise RuntimeError(f"MCP error calling {method}: {data['error']}")
        return data.get("result")

    async def connect(self) -> None:
        await self._call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "hgai-agentchat", "version": "0.1.0"},
            },
        )
        await self._call("notifications/initialized", notification=True)

    async def list_tools(self) -> List[dict]:
        result = await self._call("tools/list")
        return result["tools"]

    async def call_tool(self, name: str, arguments: dict) -> str:
        result = await self._call("tools/call", {"name": name, "arguments": arguments})
        parts = result.get("content", [])
        texts = [p["text"] for p in parts if p.get("type") == "text"]
        return "\n".join(texts) if texts else json.dumps(result)

    async def close(self) -> None:
        await self._client.aclose()


class HgaiMcpToolkit(Toolkit):
    """An Agno Toolkit whose tools are generated dynamically from whatever
    the resident hgai MCP server's `tools/list` currently returns — stays
    correct automatically as hgai's own tool set grows, with no
    hand-written per-tool wrapper to keep in sync."""

    def __init__(self, client: HgaiMcpClient, functions: List[Function]):
        self._client = client
        super().__init__(name="hgai_mcp", tools=functions)

    @classmethod
    async def connect(cls, bearer_token: str, url: Optional[str] = None) -> "HgaiMcpToolkit":
        """Handshake with the resident MCP server and wrap its current tool
        list. `bearer_token` should be a JWT scoped to the account on whose
        behalf this chat turn is running (see engine.build_agent) — not a
        shared service credential — so that whenever hgai_module_mcp's tool
        implementations gain per-account RBAC checks, this chat engine is
        already passing the right identity through without further changes.

        NOTE (known gap, not introduced by this module): as of this writing
        hgai_module_mcp/server.py's tool functions do not actually check the
        authenticated account's permissions — any validated token currently
        gets full, unscoped access. Threading a real per-account JWT through
        here is still the right design; it just isn't a security boundary
        yet until that gap is closed.
        """
        if url is None:
            settings = get_settings()
            url = f"http://127.0.0.1:{settings.port}/mcp/"
        client = HgaiMcpClient(url, bearer_token)
        await client.connect()
        tools = await client.list_tools()

        functions = []
        for t in tools:
            tool_name = t["name"]

            def _make_entrypoint(name: str):
                async def entrypoint(**kwargs):
                    return await client.call_tool(name, kwargs)
                return entrypoint

            functions.append(
                Function(
                    name=tool_name,
                    description=t.get("description", ""),
                    parameters=t["inputSchema"],
                    entrypoint=_make_entrypoint(tool_name),
                    skip_entrypoint_processing=True,
                )
            )
        return cls(client, functions)

    async def close(self) -> None:
        await self._client.close()
