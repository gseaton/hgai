"""MCP module descriptor for HypergraphAI."""

from contextlib import asynccontextmanager


class _AuthMiddleware:
    """ASGI middleware that authenticates the MCP sub-app's callers.

    Accepts the same credentials as the REST API — a JWT for an active
    account, or one of the configured HGAI_PRIMARY_API_KEY /
    HGAI_SECONDARY_API_KEY values (a full-admin credential). A missing,
    invalid or expired credential, or a JWT for an unknown or inactive
    account, returns 401 before the request reaches the MCP handler.

    The resolved account is published for the duration of the request
    (server.set_caller) so every tool authorizes as the caller.
    """

    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

        from hgai.core.auth import authenticate_token
        account = await authenticate_token(token)
        if account is None:
            response = _unauthorized_response()
            await response(scope, receive, send)
            return

        from .server import reset_caller, set_caller
        marker = set_caller(account)
        try:
            await self._app(scope, receive, send)
        finally:
            reset_caller(marker)


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
    values as a Bearer token. Authorization: each tool runs as the
    authenticated account under the same rules as the REST API.
    """

    name = "mcp"
    version = "0.1.0"
    description = (
        "MCP (Model Context Protocol) — exposes hypergraph CRUD and SHQL "
        "query operations as MCP tools for AI agents"
    )

    def get_app(self):
        from .server import create_mcp_server, mcp
        self._mcp = mcp
        return _AuthMiddleware(create_mcp_server())

    @asynccontextmanager
    async def lifespan(self):
        async with self._mcp.session_manager.run():
            yield
