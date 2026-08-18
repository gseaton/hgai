# HypergraphAI — Timeline, Funding & Go-to-Market Plan

**Prepared:** 2026-08-17
**Status:** Working planning document — every dollar figure, valuation, and
adoption number below is an **illustrative estimate** built from stated
assumptions (Section 1) and current third-party market data (Section 9,
cited). Nothing here is a commitment, an appraisal, or investment advice.
Treat this as a first-pass model to pressure-test and revise with counsel,
an accountant, and (once one exists) a board — not as a document to hand
an investor unedited.

---

## 0. Executive Summary

- **Product structure:** an open-source core, **hgx (HypergraphX)**, with
  the commercial product, **HypergraphAI**, shipping as a module on top of
  it — a standard, de-risked open-core split, and one that fits this
  codebase's existing "everything is a module" architecture without a
  redesign (see Section 2).
- **Technical delivery:** hgx v0.1 (OSS) and HypergraphAI v0.1 (module)
  ship together at **month 3**. First alpha commercial-hosting customer
  at **month 6–9**. Vendor/partner training programs launch **month 6–9**.
  General availability of commercial hosting at **month 12–15**.
- **Funding ask:** **$3.0M seed**, recommended at **~$11M pre-money /
  ~$14M post-money** (≈21% new-investor ownership before accounting for
  a standard option-pool top-up — see Section 6).
- **Runway:** modeled burn (10-person team, ramped by month 3) puts pure
  burn-funded runway at **~17 months** with zero revenue credit, and
  **~24 months** net of a conservative revenue ramp starting at the alpha
  stage. **Recommendation: treat 17 months as the real risk-managed
  runway and start Series A conversations by month 14–15** — the revenue
  upside should improve terms, not be relied on for solvency.
- **Company structure:** Delaware C-Corp (standard), with Delaware
  **Public Benefit Corporation** flagged as a serious, equally fundable
  alternative given the open-source/mission framing already present in
  this project (Section 7).

---

## 1. Assumptions & Methodology

State these up front because every downstream number depends on them —
change any one and the tables in Sections 4–5 and 8–9 should be rebuilt,
not hand-adjusted.

- **Start date:** Month 0 = September 2026 (adjust all calendar dates in
  Section 3 if the actual kickoff differs).
- **Staffing:** the 10 roles specified in this planning request, US-based
  or US-equivalent remote compensation, fully ramped by month 3.
- **Compensation:** market-rate-ish, seed-stage-discounted base salaries
  (below big-tech, above bootstrap-nonprofit); a 1.3× burden multiplier
  for payroll tax, benefits, and standard overhead. No equity value is
  modeled in cash burn (equity comp is assumed via the option pool, not
  cash).
- **Non-personnel costs:** infrastructure/cloud, tooling, legal/
  accounting, insurance, marketing/GTM, office/travel, and a security/
  compliance line starting ahead of GA (SOC 2 readiness), phased in as
  the company scales — see Section 4.2.
- **Revenue:** built bottom-up from the stated milestone dates (alpha at
  month 6–9, GA at month 12–15) with conservative-but-real customer
  count and pricing assumptions stated in Section 8 — not backed into
  from a target.
- **Market data:** cited to specific sources retrieved 2026-08 (Section
  9). Figures vary meaningfully across providers; ranges are shown, not
  single-point "truths."

---

## 2. Product & Company Structure

**hgx (HypergraphX)** — the open-source core: hypernode/hyperedge storage,
HQL/SHQL query engines, the storage abstraction, and the MCP server. MIT
licensed. This is the adoption engine — developers and agent builders can
self-serve, integrate, and contribute without a sales conversation.

**HypergraphAI** — the commercial product, packaged as one or more modules
on top of hgx: managed hosting, enterprise RBAC/Spaces at scale, mesh
federation across an organization's servers, advanced retrieval/
inferencing, SLA-backed support, and admin tooling. This is not a
re-architecture — the codebase's existing module convention
(`hgai_module_*`, mounted conditionally at startup) already separates
core engine from add-on capability; the open-core split is a packaging
and licensing decision layered on architecture that already exists.

**Why this split, briefly:** it's the proven open-core motion (MongoDB,
Elastic, HashiCorp, Databricks) — open source drives top-of-funnel
adoption and trust; the commercial module monetizes the operational
burden (hosting, scale, support) enterprises will pay to not own
themselves. Section 8 builds the GTM model around this explicitly.

---

## 3. Technical Delivery Timeline

| Milestone | Target | Description |
|---|---|---|
| hgx v0.1 (OSS) + HypergraphAI v0.1 (module) release | **Month 3** (Dec 2026) | First public open-source release; commercial module available, self-hosted only |
| First alpha commercial-hosting customer | **Month 6–9** (Mar–Jun 2027) | 1–3 design-partner customers on managed hosting, discounted/pilot terms |
| Vendor / partner training programs launch | **Month 6–9** (Mar–Jun 2027) | First certification cohort; groundwork for a systems-integrator/reseller channel |
| General availability, commercial hosting | **Month 12–15** (Sep–Dec 2027) | Public pricing, self-serve + sales-assisted signup, SLA-backed |

This timeline is the spine every other section is built against — the
staffing ramp (Section 4) is sized to hit month 3; the revenue model
(Section 8) doesn't assume any hosting revenue before month 6 and treats
month 13 (GA midpoint) as the inflection point for growth.

---

## 4. Staffing Plan & Burn Model

### 4.1 Roles and ramp

| Role | Starts | Illustrative base | Notes |
|---|---|---|---|
| CEO | Month 0 | $170K | Founder |
| CTO / Chief Scientist | Month 0 | $190K | Founder; architecture + research/IP, not day-to-day eng management |
| Tech Lead | Month 1 | $165K | Day-to-day engineering management of the dev team — distinct from CTO |
| Developer 1 | Month 1 | $150K | |
| Developer 2 | Month 1 | $150K | |
| Developer 3 | Month 2 | $145K | |
| Developer 4 | Month 3 | $145K | Full dev team (4) reached by the month-3 OSS release, as specified |
| CPO / Sales / BD | Month 2 | $160K | + variable/commission comp not modeled in base burn |
| COO / CFO | Month 3 | $160K | **Consider fractional/part-time for the first 6–9 months** — a common seed-stage lever to cut ~$60-80K of year-one cash burn; modeled here at full-time for simplicity |
| Admin / Ops | Month 3 | $75K | |

**Total base at full ramp (10 people): $1,510,000/yr.**
**Fully burdened (×1.3): $1,963,000/yr ≈ $163.6K/month.**

### 4.2 Non-personnel cost phases

| Phase | Monthly avg | Drivers |
|---|---|---|
| Months 0–3 | ~$10K/mo (+ **one-time ~$45K** at month 1 for incorporation + seed-round legal) | Dev infra, minimal tooling, formation |
| Months 4–9 | ~$17K/mo | OSS launch marketing, insurance begins (~mo 6), legal/accounting ongoing |
| Months 10–15 | ~$28K/mo | Hosting infra for alpha→GA customers, GA launch marketing, SOC 2 readiness prep |
| Months 16–24 | ~$37K/mo | Scaling hosting infra, sustained marketing, insurance (incl. tech E&O), ongoing security/compliance |

### 4.3 Cumulative burn by milestone

| Milestone | Cumulative personnel | Cumulative non-personnel | **Total cumulative spend** | Cumulative projected revenue (§8) | **Net cumulative burn** |
|---|---|---|---|---|---|
| 3 mo | $305K | $75K | **$380K** | $0 | **$380K** |
| 6 mo | $797K | $126K | **$923K** | ~$0 | **$923K** |
| 9 mo | $1,289K | $177K | **$1,466K** | ~$12K | **~$1,455K** |
| 12 mo | $1,781K | $261K | **$2,042K** | ~$65K | **~$1,977K** |
| 18 mo | $2,765K | $453K | **$3,218K** | ~$410K | **~$2,808K** |
| 24 mo | $3,749K | $675K | **$4,424K** | ~$1,440K | **~$2,984K** |

**Read this two ways, deliberately:**

- **Burn-only (no revenue credit):** $3M is exhausted around **month
  17** — comfortably past GA (month 12–15), which is the point.
- **Net of projected revenue:** cumulative net burn stays just under $3M
  through **month 24**, if the Section 8 revenue ramp lands roughly on
  schedule.

**Recommendation:** plan and communicate runway off the burn-only number
(~17 months). Start Series A conversations no later than **month 14–15**
— right as GA lands and before cash gets tight — and treat the
revenue-netted extension as upside that improves Series A terms, not as
a reason to delay fundraising.

---

## 5. Funding Requirement Summary by Checkpoint

| Checkpoint | Headcount | Cumulative spend to date | Key milestone hit |
|---|---|---|---|
| **3 months** | 10 (full ramp) | $380K | hgx v0.1 + HypergraphAI v0.1 released |
| **6 months** | 10 | $923K | Alpha customer conversations underway |
| **9 months** | 10 | $1,466K | 1–3 alpha hosting customers live; first training cohort |
| **12 months** | 10 | $2,042K | Approaching/at GA |
| **18 months** | 10 (+ plan Series A hires, not funded by seed) | $3,218K | GA live 3–6 months; Series A should be closing around here |
| **24 months** | 10 (baseline) | $4,424K | Scaling — additional headcount (customer success, DevRel, more engineering) should be funded by Series A, not assumed within this seed budget |

---

## 6. Seed Round: Valuation & Ownership

**Market context (2026, current data — see Section 9 for sources):**
AI-sector seed rounds are pricing at a real premium to non-AI peers —
one dataset puts median AI seed **pre-money around $17.9M** with median
deal size **~$4.6M**; another (Carta-sourced) puts the broader seed
median as high as $24M pre-money. These are market-wide medians across a
cohort that includes many high-hype foundation-model and agent startups
— **not** a number to anchor to uncritically for a pre-revenue,
ten-person, single-market infrastructure company.

**Recommendation: price conservatively relative to the AI-hype median.**
Overpricing a seed round without revenue traction is one of the most
common causes of a difficult flat or down Series A. A fair, fundable,
"common sense" range for this stage and team size:

| | Conservative | **Recommended** | Aggressive (market-median-adjacent) |
|---|---|---|---|
| Pre-money | $9M | **$11M** | $15M |
| Raise | $3M | **$3M** | $3M |
| Post-money | $12M | **$14M** | $18M |
| New-investor ownership | 25.0% | **~21.4%** | ~16.7% |

**Option pool note:** if a new employee option pool (commonly ~10% of
post-money) is created as part of the round — standard practice, and
something most seed investors will require — it's typically carved from
the **pre-money** shares, i.e. it dilutes founders, not the incoming
investor. At the recommended terms, founders' effective post-round
ownership is closer to **~100% − 21.4% (investor) − 10% (pool) ≈ 68.6%**,
not 78.6%. Model this explicitly in any actual cap table before signing
a term sheet.

---

## 7. Company Structure

| Structure | VC-fundable? | Fit for this company |
|---|---|---|
| **C-Corp (Delaware)** | Yes — the standard | **Recommended default.** Preferred stock, standard ISO option pools, QSBS (IRC §1202) eligibility for founders/early employees on a future exit, universally expected by institutional investors. |
| **Public Benefit Corp (Delaware)** | Yes — identical mechanics to a C-Corp | **Recommended alternative, worth serious consideration.** Same fundability, same stock/option mechanics, same QSBS treatment — plus a charter-level commitment to a stated public benefit. Given this project's own open-source/AI-alignment framing already present in its design materials, a PBC charter (e.g., committing to open-source stewardship of hgx, or responsible-AI-agent principles) is a genuine, low-cost differentiator with some investors, not just a symbolic gesture. |
| LLC | Technically possible pre-raise | **Not recommended once raising institutional money.** Pass-through taxation creates real complications for VC funds (many are tax-exempt LPs sensitive to UBTI) and there's no clean preferred-stock mechanism. Common pattern: convert LLC → Delaware C-Corp immediately before a priced round if starting from an LLC. |
| S-Corp | No | **Ruled out.** Capped at 100 shareholders, one class of stock, no entity/non-US shareholders — incompatible with VC preferred stock and fund investors. |
| LLP | No | **Ruled out.** A professional-services partnership structure (law, accounting firms); no standard equity/option mechanism VCs expect, and doesn't fit a product company at all. |

**Recommendation:** incorporate as a **Delaware C-Corp**, and have the
founders make a deliberate, informed choice between standard C-Corp and
**PBC** before signing formation documents — it's a one-time decision
that's expensive to revisit later, and the PBC option costs essentially
nothing in fundability to keep on the table given this project's
existing character.

---

## 8. Go-to-Market Strategy

Built around the open-core split from Section 2 — three motions, in
sequence, each feeding the next:

**1. Product-led adoption (hgx, OSS)** — months 0–ongoing. Developers and
agent builders self-serve hgx directly from GitHub; the MCP server means
integration into an existing agent stack is close to zero-config. No
sales motion — the goal is downloads, stars, community MCP-ecosystem
presence, and a funnel of self-identified power users.

**2. Direct commercial hosting (HypergraphAI)** — alpha at month 6–9, GA
at month 12–15. Convert the highest-intent slice of the OSS community
plus direct outbound to design-partner customers; alpha pricing is
deliberately discounted in exchange for product feedback and case-study
rights. GA moves to published pricing with a self-serve tier and a
sales-assisted enterprise tier.

**3. Partner / training channel** — launches month 6–9 alongside the
first alpha customers. Certification programs and a reseller/
implementation-partner track let systems integrators and consulting
firms carry HypergraphAI into their own client relationships without
requiring a large direct sales team. **This motion is not hypothetical
for this project** — the defense-sector business-development materials
already produced in this repository (`docs/decks/demo-bus-dev-20260817/`
and `docs/decks/demo-spec-ops-20260817/`) are a direct, already-built
example of the kind of partner-enablement content this channel runs on.

---

## 9. Market Analytics

Figures below are cited to specific sources retrieved 2026-08; providers
disagree meaningfully, so ranges are shown deliberately rather than a
single cherry-picked number.

**Knowledge graph market:** 2026 market size estimates range **$1.9B–
$2.9B** across providers, with CAGR estimates ranging **19%–38%**
depending on methodology and forecast window. One frequently-cited
figure: **$9.88B by 2032 at a 31.6% CAGR** (MarketsandMarkets, via
GlobeNewswire). Treat any single figure in this range as directional, not
precise — the spread itself is informative about how immature/fast-moving
this market categorization still is.

**Enterprise AI agent adoption:** per Gartner-sourced reporting, **80% of
enterprise applications shipped or updated in Q1 2026 embed at least one
AI agent**, up from 33% in 2024 — but a more conservative, arguably more
decision-relevant figure is that **only 31% of enterprises have at least
one agent actually in production** (banking/insurance leading at 47%;
healthcare/government trailing at 14–18%). Gartner separately projects
**40% of agentic AI projects will be canceled by end of 2027** — a real
signal that "shipped a pilot" and "sustained production value" are very
different bars, worth holding onto for any investor conversation about
adoption risk.

**MCP ecosystem specifically:** MCP server downloads grew from **~100K
(Nov 2024) to over 8M (Apr 2025)**; **5,800+ MCP servers and 300+ clients**
now exist; **Fortune 500 MCP implementation reached ~28% within 18 months**
of launch, with OpenAI, Google, Microsoft, and AWS all adopting the
protocol alongside Anthropic, under Linux Foundation governance. This is
the single strongest, most concrete data point supporting this company's
core bet — MCP is not a niche Anthropic-only standard, it's becoming the
default agent-integration layer industry-wide, and hgx/HypergraphAI is
built MCP-native from day one rather than as a bolt-on.

**TAM/SAM (illustrative, not independently modeled bottom-up):**
treating "knowledge graph market" as a proxy undersells this company's
actual addressable market, since agent-memory infrastructure is an
adjacent, currently-uncategorized spend line that's growing off the MCP
adoption curve above rather than off legacy knowledge-graph budgets. A
defensible near-term SAM: AI-forward enterprises with at least one agent
in production (the 31% figure above) that need structured, persistent
agent memory — a real but currently unquantified segment; **before using
a specific SAM/TAM dollar figure in an actual pitch, commission or
independently build a bottom-up estimate rather than relying on
knowledge-graph-market proxies**, which is a category this product only
partially overlaps.

**Sources:**
- [Knowledge Graph Market Surges to $9.88 billion at a CAGR 31.6% by 2032 — MarketsandMarkets](https://www.globenewswire.com/news-release/2026/06/29/3319085/0/en/knowledge-graph-market-surges-to-9-88-billion-at-a-cagr-31-6-by-2032-report-by-marketsandmarkets.html)
- [Knowledge Graph Market Trends Support A 22.5% CAGR Outlook](https://www.openpr.com/news/4600723/knowledge-graph-market-trends-support-a-22-5-cagr-outlook)
- [Global Knowledge Graph Market Size — Verified Market Reports](https://www.verifiedmarketreports.com/product/knowledge-graph-market/)
- [AI Startup Fundraising Trends 2026 (Seed to Series B) — Eqvista](https://eqvista.com/ai-startup-fundraising-trends/)
- [AI Startup Valuations in 2026: Seed Rounds 42% Above Non-AI Baselines — AgentMarketCap](https://agentmarketcap.ai/blog/2026/04/06/ai-early-stage-valuation-premium-2026-seed-series-a-vc-funding)
- [Average Seed Valuation in 2026: $24M Median (Carta Data) — Flowjam](https://www.flowjam.com/blog/seed-round-valuation-2025-complete-founders-guide)
- [Agentic AI Adoption Statistics for 2026 — First Page Sage](https://firstpagesage.com/reports/agentic-ai-adoption-statistics/)
- [AI Agent Adoption 2026: What the Data Shows — Gartner, IDC (Joget)](https://joget.com/ai-agent-adoption-in-2026-what-the-analysts-data-shows/)
- [89% of AI Agent Pilots Never Scale: Gartner's 2026 Data](https://www.beri.net/article/ai-agent-adoption-enterprise-2026-gartner-idc)
- [What is Model Context Protocol? The Enterprise Guide to MCP Adoption — Airia](https://airia.com/blog/what-is-model-context-protocol-the-enterprise-guide-to-mcp-adoption/)

---

## 10. Projected Adoption & Revenue

**Illustrative only — see Section 1's methodology note.** Built bottom-up
from customer-count and pricing assumptions stated inline, not backed
into a target ARR number.

### 10.1 OSS adoption (leading indicator, not revenue)

| Checkpoint | hgx adoption signal (illustrative) |
|---|---|
| 3 mo | v0.1 released; baseline GitHub/community presence established |
| 9 mo | Early community integrations; first external MCP-ecosystem mentions |
| 15 mo | Meaningful self-serve funnel into HypergraphAI hosting trials |
| 24 mo | OSS community is the dominant top-of-funnel source for commercial hosting leads |

### 10.2 Hosting revenue ramp (illustrative pricing: $1.5K/$5K/$15K
monthly tiers, blended)

| Month | Customers | Blended MRR |
|---|---|---|
| 7 | 1 (alpha, discounted) | ~$0.5K |
| 9 | 2 | ~$2K |
| 13 (GA) | 3 | ~$9K |
| 15 | 6 | ~$24K |
| 18 | 12 | ~$60K |
| 21 | 20 | ~$110K |
| 24 | 30 | ~$180K (**~$2.16M annualized**) |

### 10.3 Cumulative revenue by checkpoint, all streams

| Checkpoint | Hosting (cumulative) | Training/partner (cumulative) | Professional services (cumulative) | **Total** |
|---|---|---|---|---|
| 9 mo | ~$4K | ~$7.5K | $0 | **~$12K** |
| 12 mo | ~$13K | ~$23K | ~$30K | **~$65K** |
| 18 mo | ~$201K | ~$90K | ~$120K | **~$410K** |
| 24 mo | ~$941K | ~$220K | ~$280K | **~$1,440K** |

This is a growth-off-a-small-base curve, deliberately: it does not
assume GA-day traction, it assumes the alpha phase (month 6–9) produces
real but modest revenue, and growth accelerates only once GA (month
12–15) removes the "still in alpha" objection from enterprise buyers.

---

## 11. Funding Roadmap Beyond Seed (Directional)

Genuinely speculative this far out — shown only to demonstrate the seed
round is sized against a coherent multi-round plan, not in isolation.

| Round | Rough timing | Illustrative raise | Illustrative pre-money | Trigger |
|---|---|---|---|---|
| Seed | Month 0 | $3.0M | ~$11M | This plan |
| Series A | ~Month 15–20 | $10–15M | $40–60M | GA live + demonstrated MRR growth + OSS adoption metrics |
| Series B | ~Month 30–36 | $25–40M | $120–180M | Proven repeatable enterprise sales motion, partner-channel revenue material |

Every figure in this table should be treated as a planning placeholder,
re-derived from actual traction at the time, not a commitment.

---

## 12. Key Risks & Assumptions to Revisit

- **Revenue ramp risk:** Section 10's hosting growth curve is the single
  most load-bearing (and most speculative) assumption in this document —
  it directly determines whether net burn tracks toward the optimistic
  (~24-month) or conservative (~17-month) runway case in Section 4.3.
- **GA timing slip:** every downstream revenue assumption shifts right if
  GA slips past month 15; re-run Section 10 before relying on this plan
  if that happens.
- **Fractional COO/CFO:** modeled as full-time from month 3 for
  simplicity; using a fractional/part-time CFO for the first 6–9 months
  is a realistic way to extend runway by roughly 0.5–1 month without
  cutting anything else.
- **Compensation assumptions:** Section 4.1's salaries are illustrative
  market-rate estimates, not benchmarked against a compensation survey —
  revisit before making actual offers.
- **Agentic-AI adoption is real but uneven:** Section 9's own data shows
  a wide gap between "shipped a pilot" (80%) and "sustained production
  use" (31%), with Gartner projecting 40% of agentic AI projects
  canceled by 2027 — the GTM plan and investor narrative should
  acknowledge this honestly rather than assume a smooth adoption curve.
