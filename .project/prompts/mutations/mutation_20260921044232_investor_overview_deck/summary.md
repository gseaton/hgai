# Mutation Summary

## Intent
Produce an investor / VC / tech-media slide deck (Markdown) explaining semantic knowledge hypergraphs in the AI era and HypergraphAI's implemented features, use cases, market, competition, business model, go-to-market and funding plan.

## Context
- The repo already has an older `docs/investor-pitch-deck.md` (unsourced market figures, "19 MCP tools", check-mark competitor matrix, unverifiable "production-ready" claims) and a careful `docs/operations/timeline-funding-20260817.md` (assumptions, staffing, burn, revenue ramp, sourced market data, explicit warning to build TAM/SAM bottom-up). The new deck follows the latter's discipline.
- Features were taken from the current code and docs, not from earlier decks: 30 MCP tools (counted from the server), five Note scopes, HgNexus (the user's name for the `hgai_module_agentchat` chat module), export/import, seeds, Help, Visualize, parameterized queries, project inference, Spaces/RBAC, meshes; ~26k source lines and 346 tests were counted.
- Proof points come from work done in this repository: the verified Alchemy fraud-graph generation and the verified queries.

## What Changed and Why
- **Honesty layer**: every capability is marked ✅ live, 🛠️ enabled by live building blocks, or 🗺️ planned. This matters for the two use cases the request emphasized: agent working memory and cross-vendor persisted memory are *patterns on live primitives* (no automatic expiry/promotion; HgNexus sessions are pinned to one model), and the deck says so, together with a dedicated "Honest gaps" slide (no vector search, scale envelope, single backend, no SSO/SOC 2, no marketplace/billing yet).
- **Market analysis**: current third-party figures were researched (retrieved 2026-09-21) and cited, ranges rather than single numbers. TAM (≈ $6–14B, 2030) is top-down; SAM (≈ $0.49B) is a transparent bottom-up model whose assumptions are labelled; SOM (≈ $28M ARR by year 5, ≈ 6% of SAM) is presented as a scenario. The earlier deck's unsourced $800M SAM / $8B TAM are explicitly replaced.
- **Business model**: seven streams (hosting, subscriptions, marketplace, support, professional services, knowledge brokering, training) with tier pricing taken from the funding plan, marketplace and services details, a revenue ramp from the funding plan and a labelled five-year extension.
- **Competition**: qualitative category positioning (property graphs, RDF/semantic, hypergraph/n-ary including TypeDB as the closest rival, agent-memory layers, vector databases) with sourced facts and an explicit "where incumbents are stronger" column instead of an unverifiable check-mark matrix.
- **GTM and funding**: three motions, phased timeline (month 0 = Sept 2026), channels, KPIs, seed ask ($3M, ≈ $11M pre-money recommended), use of funds derived from the plan's burn model, milestones, and media story angles.
- **Verification**: every SHQL block in the deck was parsed/validated and executed against the live graphs (Alchemy, `eden`, `hello-world`); tables were checked for consistent columns; arithmetic (TAM/SAM/SOM, mix, use of funds) was recomputed.

## Key Decisions
- Used **HgNexus** as the product name per the request, noting it is implemented as the `hgai_module_agentchat` module.
- Kept the funding plan's illustrative numbers (tiers $1.5K/$5K/$15K, ramp, seed terms) for consistency; marketplace take rate (20–30%), services price ranges, SAM assumptions and years 3–5 ARR are the deck's own labelled assumptions.
- Left placeholders where facts are not in the repo: founders' biographies, customers/partners. The disclaimer states these must be supplied and approved before distribution.
- No code, tests or existing documents were changed.
