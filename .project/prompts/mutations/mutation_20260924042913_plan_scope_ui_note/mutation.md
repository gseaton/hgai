# Mutation Log

## Modified
- **docs/architecture/sparql-to-shql-conversion-plan.md** — Added a "A note on scope: this plan covers the backend only" paragraph after Phase 7 (Packaging), before §6 (Recommendation & next steps). States plainly that every phase in the plan delivers only a REST endpoint on a new `hgai_module_sparql_shql` module, and that a Web UI input surface, a shell command, and MCP tool exposure were never scoped anywhere in the document — not a deliberate "backend first" decision, just an unaddressed gap — and suggests these client-facing surfaces need their own deliberate scoping (their own phase(s) and effort estimate) rather than being assumed to follow automatically once the backend exists.
