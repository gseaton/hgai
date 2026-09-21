# Mutation Summary

## Intent
Produce a slide deck for enterprise, data and AI-system architects covering concepts, implementation, benefits, the architecture of HypergraphAI, how MCP integrates AI agents, feature use by humans and agents, and the requested use cases as architectures.

## Context
- The earlier investor deck was marketing-oriented. Architects need the real system boundaries, data model, failure modes and limitations, so the deck was built from the code (module mounting in `hgai/main.py`, storage ABCs and indexes, MCP module and middleware, agent-chat engine and toolkits, auth, SHQL/inference/mesh engines, configuration) and from measurements made in this repository (the 5.5M-record graph build, query timings, an inference test that did not finish on a 187k-edge graph).

## What Changed and Why
- **New deck**: structured as Why/What → System → Data → Query/Inference/Federation → Security → MCP → HgNexus → Features → Use cases → Modeling → Reference architectures/NFRs/adoption → Appendix. Every use case in the request has an architecture slide with its status (✅ implemented, 🛠️ pattern on live features, 🗺️ planned, ⚠️ limitation). Every SHQL example was validated and executed against live data; tables were checked; measured numbers are labelled as measured, not promised.
- **A security finding surfaced while writing the security slides, and was verified live**: an account with role `readonly` and no permissions receives 403 from REST graph endpoints, but can read every graph through `POST /shql/query` and can list, read and *create* nodes through the MCP tools. The MCP endpoint and the SHQL router authenticate the caller but do not apply `can_access_graph` / `can_perform`; MCP writes are stamped as `mcp-agent`; an API key is a synthetic full-admin account. Consequently HgNexus's MCP tools also run unscoped for any signed-in user. The deck states this plainly (authorization coverage matrix, design-around guidance, planned fix).
- **Corrections**: my earlier investor deck and four Help topics (written earlier in this session) had implied per-user permission scoping for agents/MCP and per-agent audit attribution. Those statements were corrected, and a misleading code comment was fixed. No behavior was changed.

## Key Decisions
- **Documented rather than fixed** the authorization gap: enforcing permissions in MCP/SHQL changes access semantics for existing users/tools and deserves an explicit decision; the deck lists it as the first roadmap item, and the summary to the user offers to implement it.
- Kept plain-text diagrams (no Mermaid) so the file renders in any Markdown viewer, consistent with earlier decks.
- Verification: SHQL blocks parsed/validated/executed (20 rows in ≈ 4 s on the 3.6M-node graph; `hello-world` example returns Moe and Curly); tables have consistent columns; full test suite unchanged (344 passed, 2 pre-existing mesh-ping failures).
