"""AI Agent Chat module descriptor for HypergraphAI.

Phase 1: vendor/model CRUD only. Chat sessions, the Agno-backed agent
engine, and the resident-MCP-server toolkit land in Phase 2.
"""


class AgentChatModule:
    name = "agentchat"
    version = "0.1.0"
    description = (
        "AI Agent Chat — multi-vendor (Anthropic/OpenAI/xAI) LLM chat with "
        "an admin-managed vendor/model catalog, at /api/v1/agent"
    )

    def get_router(self):
        from .api_router import router
        return router
