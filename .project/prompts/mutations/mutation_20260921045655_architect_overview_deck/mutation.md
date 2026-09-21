# Mutation Log

## Created
- **docs/marketing/hypergraphai-overview-enterprise-20260921045025.md** — ~1,150-line Markdown slide deck for enterprise / data / AI-system architects (50 numbered slides in 11 parts + appendix): concepts and decision matrix; system context and container views, module and storage architecture, request flow; logical/physical data model, identity, time and provenance; SHQL, inference and mesh federation architecture; authentication and an authorization coverage matrix; MCP architecture (protocol, implementation, sequence, tool risk tiers, integration patterns, guardrails); HgNexus architecture; feature map for humans and agents; the eight use cases as architectures; modeling rules and anti-patterns from the 5.5M-record build; reference architectures, NFRs, deployment, sizing, adoption path, gaps and roadmap; appendix (tool catalog, REST surface, SHQL cheat sheet, configuration, glossary).

## Modified (corrections to earlier statements found to be inaccurate while researching the deck)
- **docs/marketing/hypergraphai-overview-investor-20260921043558.md** — Removed/qualified claims that agents over MCP or HgNexus are scoped by RBAC or act with the user's permissions; removed the claim that writes are attributed per agent identity (they are stamped `mcp-agent`); added an "Authorization on MCP / SHQL" row to the honest-gaps slide and adjusted the security objection-handling line.
- **docs/help/notes/web-ui/ai-chat.md**, **docs/help/notes/integration/mcp-server.md**, **docs/help/notes/integration/authentication.md**, **docs/help/notes/admin/accounts-roles.md** — Replaced "acts with your account's permissions" / "only sees what your account may see" with the actual behavior: MCP tools and SHQL authenticate but do not apply per-graph/space permissions; guidance to isolate the endpoint and restrict HgNexus.
- **hgai_module_agentchat/engine.py** — Docstring of `build_agent` corrected (comment only, no behavior change): the minted JWT identifies the caller but does not scope MCP tool data access.

## Not modified
- No application logic, tests or configuration changed. The authorization gap itself was documented, not fixed.
- Temporary verification data (a probe account and one probe node in `eden`) was created and removed.
