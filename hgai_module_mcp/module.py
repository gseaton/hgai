"""MCP module descriptor for HypergraphAI."""


class MCPModule:
    """MCP (Model Context Protocol) module.

    Exposes HypergraphAI operations as MCP tools for use by AI agents
    via a streamable HTTP app mounted at /mcp.
    """

    name = "mcp"
    version = "0.1.0"
    description = (
        "MCP (Model Context Protocol) — exposes hypergraph CRUD and HQL "
        "query operations as MCP tools for AI agents"
    )

    def get_app(self):
        from .server import create_mcp_server
        return create_mcp_server()
