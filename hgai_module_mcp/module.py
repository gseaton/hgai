"""MCP module descriptor for HypergraphAI."""

from contextlib import asynccontextmanager


class _ApiKeyMiddleware:
    """ASGI middleware that validates Bearer API keys for the MCP sub-app.

    Accepts the same HGAI_PRIMARY_API_KEY / HGAI_SECONDARY_API_KEY values
    that are accepted by the REST API.  A missing or unrecognised token
    returns 401 before the request reaches the MCP handler.
    """

    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        # Extract Bearer token from Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

        from hgai.core.auth import _resolve_api_key
        if not _resolve_api_key(token):
            # Also accept a valid JWT so human callers can use the MCP endpoint
            from hgai.config import get_settings
            from jose import jwt, JWTError
            settings = get_settings()
            authed = False
            if token:
                try:
                    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                    authed = bool(payload.get("sub"))
                except JWTError:
                    pass
            if not authed:
                response = _unauthorized_response()
                await response(scope, receive, send)
                return

        await self._app(scope, receive, send)


def _unauthorized_response():
    """Return a minimal ASGI 401 response callable."""
    async def respond(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", b"Bearer"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"detail":"Not authenticated"}',
        })
    return respond


class MCPModule:
    """MCP (Model Context Protocol) module.

    Exposes HypergraphAI operations as MCP tools for use by AI agents
    via a streamable HTTP app mounted at /mcp.

    Authentication: all requests must carry either a valid JWT bearer token
    or one of the configured HGAI_PRIMARY_API_KEY / HGAI_SECONDARY_API_KEY
    values as a Bearer token.
    """

    name = "mcp"
    version = "0.1.0"
    description = (
        "MCP (Model Context Protocol) — exposes hypergraph CRUD and HQL "
        "query operations as MCP tools for AI agents"
    )

    def get_app(self):
        from .server import create_mcp_server, mcp
        self._mcp = mcp
        return _ApiKeyMiddleware(create_mcp_server())

    @asynccontextmanager
    async def lifespan(self):
        async with self._mcp.session_manager.run():
            yield
