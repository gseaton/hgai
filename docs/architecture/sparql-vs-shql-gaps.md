# SPARQL vs. SHQL — Capability Gap Priorities

This is a follow-up to [`sparql-to-shql-conversion-plan.md`](sparql-to-shql-conversion-plan.md), which laid out a phased transpiler plan and a full feature-by-feature comparison table. That table listed roughly a dozen SPARQL capabilities SHQL has no equivalent for. This document answers the follow-up question directly: **which of those gaps are actually worth closing, and in what order — if any?**

This document's Tier 1–3 recommendations have since been folded back into the conversion plan itself: Tier 1 (`VALUES`, output-only `BIND`, `SUM`/`AVG`/`MIN`/`MAX`) and Tier 2 (`ASK`, `^p`, fixed-length path chains) are built into Phases 2.5 and 4; Tier 3 (`FILTER EXISTS`/`NOT EXISTS`, `MINUS`) ship as the documented approximations this tier recommended, in Phase 3. Tier 4 and Tier 5 remain explicit non-goals, threaded into the plan's Phase 5 rejection layer with their specific reasoning intact rather than a generic "unsupported."

## Bottom line

Most real-world SPARQL queries live inside a narrow subset — basic graph patterns, `OPTIONAL`, `FILTER`, `ORDER BY`/`LIMIT` — and that subset is already well covered by the conversion plan's Phases 1–4. Of the remaining gaps, only three are both common enough and cheap enough to justify building into v1: **`VALUES`, numeric aggregates (`SUM`/`AVG`/`MIN`/`MAX`), and a restricted form of `BIND`.** Several of the more expensive-looking gaps — `CONSTRUCT`, `DESCRIBE`, `SERVICE`, SPARQL Update — aren't really gaps to close at all; they're places where SPARQL is solving a problem HGAI already solves a different, better-fitted way, and closing them would mean building a worse version of something that already exists. The recommendation below is to close three gaps deliberately, document the rest as explicit non-goals, and revisit only if a concrete use case demands it.

## How priority is scored

Every gap is scored on three axes, not one:

1. **Real-world usage frequency** — how often does this construct actually show up in SPARQL queries people write, versus academic/exhaustive-coverage corner cases?
2. **Engineering cost, and *where* it lands** — this matters more than raw effort. A gap closeable entirely inside the new transpiler module is low-risk (self-contained, no blast radius). A gap that requires extending `hgai_module_shql/engine.py` itself is higher-risk (touches the shared query engine every other SHQL consumer depends on). A gap that requires changing `hgai/core/rdf_import.py`'s mapping rules is a *third*, different kind of cost — it's not a query-time problem at all, it's a data-preservation problem at import time.
3. **Does an adequate workaround already exist?** Several "missing" features have a workaround that's good enough in practice (e.g. `ASK` via `SELECT` + `limit: 1`), which should lower their priority even if the frequency/cost numbers alone would suggest otherwise.

## A cross-cutting option: push computation into the transpiler, not the engine

Before ranking anything, one strategic point changes several of the cost estimates from the earlier plan: **a SPARQL construct doesn't need an SHQL engine change just because SHQL's query language has no matching keyword.** The transpiler can fetch a broad, unfiltered result set from SHQL (a plain `SELECT`-shaped query, no `aggregate:` block) and then perform SPARQL-semantic computation — aggregation, simple `BIND` expressions, even an `ASK` boolean check — as a post-processing step in the transpiler itself, entirely outside `hgai_module_shql/engine.py`.

Concretely, this reclassifies from "requires an SHQL engine change" to "transpiler-only":

- **`SUM`/`AVG`/`MIN`/`MAX`/`GROUP_CONCAT`/`SAMPLE`** — compute over the fetched rows client-side; SHQL's own `aggregate:` block (currently `count`/`group_by` only) never needs to grow new reducers.
- **`BIND`, for the common case** — a computed value used only in the final projected output (string concatenation, simple arithmetic on already-bound fields) can be evaluated after SHQL returns rows, not during pattern matching.
- **`ASK`** — run the translated `SELECT` with `limit: 1`, return whether it came back non-empty. (This one needed no reclassification — it was already this cheap — but it's the clearest illustration of the pattern.)
- **A `MINUS`-shaped approximation** — run the main pattern and the excluded pattern as two separate SHQL queries, then subtract row sets client-side by shared-variable key. Not fully equivalent to SPARQL's `MINUS` semantics (see Tier 3), but considerably better than the `OPTIONAL`+`FILTER(!BOUND(...))` approximation, and still zero SHQL engine changes.

**The catch:** this trades server-side efficiency for engineering safety, and it has a real ceiling. SHQL's internal node/edge search caps a single pattern's candidate fetch at 2,000 documents (`hgai_module_shql/engine.py`, the `search(..., limit=2000)` calls behind `node:`/`edge:` pattern matching) regardless of the `limit:` the query itself requests. A transpiler that fetches "everything" to aggregate client-side is implicitly relying on the true match count staying under that ceiling — past it, the aggregation is silently *incomplete*, not merely slow. This is an acceptable tradeoff for the exploratory, small-to-medium-graph queries this conversion feature is realistically aimed at, but it must be documented as a known limitation, not quietly assumed away. If aggregation over graphs regularly exceeding a few thousand matched candidates ever becomes a real requirement, that's the point at which extending SHQL's own `aggregate:` block server-side (a genuine engine change) becomes the right call instead.

## Priority tiers

### Tier 1 — Build now (v1)

| Feature | Frequency | Cost | Workaround exists? | Verdict |
|---|---|---|---|---|
| `VALUES` (inline data) | High — routine in real queries | Transpiler-only: unroll into a `union:` of literal-bound branches at translate time | None adequate | **Build.** Purely mechanical, no engine risk, closes a common gap completely. |
| `SUM`/`AVG`/`MIN`/`MAX` | High — the most common aggregate functions after `COUNT` | Transpiler-only (client-side, see above), capped at 2,000 candidates per underlying pattern | None adequate | **Build.** High value, and reclassified to transpiler-only changes the calculus entirely. |
| `BIND`, output-only case | High — very common for reshaping projected values | Transpiler-only when the bound variable is used *only* in `SELECT`, not as a join key for a later pattern or inside an upstream `FILTER` | Partial (can often restructure the query by hand) | **Build**, with that one restriction stated plainly in user-facing docs rather than silently failing on the unsupported case. |

**A note on why `VALUES` needs `union:` unrolling at all, not something simpler.** Single-field "match against a list of literals" is already native to SHQL today, two different ways: `filter: "?var.field IN [a, b, c]"` (SHQL's own FILTER mini-language) and `attributes: {field: {$in: [a, b, c]}}` inside a `node:`/`edge:` pattern (raw MongoDB operators pass straight through) — verified directly against `hgai_module_shql/engine.py`, which also confirms no `values:`-style keyword exists anywhere in the module today. Neither existing mechanism is enough for `VALUES`, though: SPARQL `VALUES` can bind several variables at once per row, and — more fundamentally — it can inject a binding for a variable with no corresponding pattern at all, which nothing in SHQL does today, since every `node:`/`edge:` pattern derives its binding from an actual document search. Hence the `union:` translation this tier recommends, which is correct and general regardless of that gap.

There's a narrower, cheaper alternative worth flagging here as a *possible future SHQL engine enhancement* (explicitly not part of this Tier 1 "build now" recommendation — it's a genuine `hgai_module_shql/engine.py` change, not transpiler-only): the node pattern's `id:` key currently accepts only a single literal or `?var` (`_eval_node_pattern`'s `node_id = pattern.get("id")`), even though the storage filter it builds, `HypernodeSearchFilters.node_ids_in`, already accepts a list — the search layer can already do a real multi-id match, `id:` on the YAML surface just never exposes it. Letting `id:` accept a list would let the transpiler handle the common "`VALUES` enumerates candidate ids for one node pattern" case (e.g. `VALUES ?person { ex:alice ex:bob ex:carol }`) as a single node pattern instead of an N-branch `union:` — cheaper for that common sub-case, though it wouldn't help the multi-variable-row case `union:` unrolling already handles generally. Worth a separate look if `VALUES` usage in practice turns out to be dominated by that single-variable shape; not a blocker for shipping the `union:` approach now.

### Tier 2 — Build if cheap (stretch goals, not blocking v1)

| Feature | Frequency | Cost | Workaround exists? | Verdict |
|---|---|---|---|---|
| `ASK` query form | Medium | Transpiler-only, trivial (`SELECT` + `limit: 1`) | N/A — this *is* the workaround | **Build** — nearly free, no reason not to. |
| Inverse property path (`^p`) | Medium | Transpiler-only — swap `seq: 0`/`seq: 1` in the translated `edge:` pattern | None | **Build** — a single, well-defined special case, not the general path algebra. |
| Fixed-length path chains (`p1/p2`) | Low–medium | Transpiler-only — expand into N sequential joined `edge:` patterns | Write the query as N separate patterns by hand | **Build if time allows** — mechanical but adds translation-stage complexity for a construct most hand-written queries don't actually need (people usually write the joins out anyway). |

### Tier 3 — Approximate only, document the caveat (don't chase full correctness)

| Feature | Frequency | Cost | Workaround exists? | Verdict |
|---|---|---|---|---|
| `FILTER EXISTS` / `NOT EXISTS` | Medium | Requires real sub-pattern evaluation inside a filter context — an `hgai_module_shql` engine change for full correctness | `OPTIONAL` + `BOUND()` covers the simple cases | **Approximate only.** Ship the `OPTIONAL`+`BOUND()` translation for simple cases, reject (don't silently mistranslate) anything more complex than that. |
| `MINUS` | Low–medium | True `MINUS` semantics (variable-compatibility-aware negation) need engine support; the transpiler-side two-query subtraction (above) is close but not identical for every case | The two-query approximation | **Approximate only**, same reasoning as `EXISTS`/`NOT EXISTS` — document the difference rather than claiming parity. |

### Tier 4 — Explicitly out of scope

| Feature | Why it's not just "low priority" — it's a non-goal |
|---|---|
| Subqueries (nested `SELECT`) | Real complexity for a construct that's rare outside expert-authored analytical SPARQL; this project's actual query authors skew toward simpler, often AI-agent-generated queries (see README's SHQL design intent) where a subquery is unlikely to be the natural way to express intent in the first place. |
| `CONSTRUCT` / `DESCRIBE` query forms | Both produce a *graph* as output, which doesn't fit SHQL's row-oriented result model at all. More importantly, HGAI already has better-fitted, native answers to what these are usually used for — hyperedge listing filtered by member node id, and full hypergraph export — that don't need to be reached through a SPARQL-shaped detour. |
| Per-pattern named graphs (`GRAPH <uri>`) | HGAI's `from:` graph-set scoping already covers the common whole-query multi-graph case. Per-pattern graph selection is an advanced, comparatively rare SPARQL feature, and supporting it would need a genuine `hgai_module_shql` redesign (per-pattern graph scoping doesn't exist in the engine today) for a capability few queries actually need. |
| `SERVICE` (federated query) | HGAI already has a federation mechanism — mesh dot-notation refs — built for this platform's actual federation topology (a mesh of known HGAI servers). `SERVICE` in real SPARQL usually targets arbitrary *external*, non-HGAI endpoints, which no amount of transpiler work can federate with anyway. A user who needs cross-server HGAI queries should write SHQL's mesh dot-notation directly, not route through a SPARQL-shaped translation for a need SHQL already serves natively and more simply. |
| SPARQL Update (`INSERT`/`DELETE`) | By design, not by oversight. HGAI's write path — REST/CRUD/shell/MCP — carries permissions, audit trail, and hyperkey deduplication that a query-language mutation path would either have to bypass (unsafe) or fully reimplement (a second, redundant maintenance surface for the same capability). This should never be built. |
| General property-path algebra (`*`, `+`, arbitrary alternation/sequencing) | The single most common real use of unbounded repetition — transitive closure — is already covered by `infer: true` on an `owl:transitive` axiom edge. Building a full path-algebra evaluator to additionally cover `*` (zero-or-more), arbitrary-depth alternation, and mixed sequencing is a large, open-ended engine investment for marginal cases beyond what Tier 1/2's targeted special cases (inverse, fixed-length chains) and the existing transitive-axiom mechanism already handle. |

### Tier 5 — A different kind of gap: import-time, not query-time

| Feature | Why it's a separate decision |
|---|---|
| Literal datatype/language (`lang()`, `datatype()`, `str()`) | This isn't a query-translation problem — the information a query would need doesn't survive `hgai/core/rdf_import.py`'s current mapping into the hypergraph at all (language tags are dropped except when picking a label; datatypes collapse into either a native Python value or a lexical string). Closing this gap means changing what RDF import *stores* — e.g. a sidecar `attributes["<key>#lang"]` or a preserved datatype marker — which is an RDF-import design decision independent of whether a SPARQL transpiler ever gets built, and should be evaluated on its own merits (is *any* consumer asking for language/datatype-aware attribute queries today?) rather than as a line item in this plan. |

## What this means for the phased plan

Against the earlier plan's phases:

- **Phase 3** (`OPTIONAL`/`UNION`/`FILTER`) should absorb the Tier 3 approximations (`EXISTS`/`NOT EXISTS` and `MINUS` via `OPTIONAL`+`BOUND()`) with their limitations called out in the same rejection/diagnostics layer that already handles unsupported constructs — an approximation that silently diverges from SPARQL semantics in edge cases is exactly the kind of thing Phase 5's diagnostics layer exists to be honest about.
- **Phase 4** (`ORDER BY`/`LIMIT`/`OFFSET`/aggregation) gains the Tier 1 numeric aggregates and Tier 2's `ASK` translation as part of its original scope, not a later increment — they were already the natural home for this work.
- A new, explicit **Phase 2.5** (`VALUES` unrolling and the two Tier 2 property-path special cases) sits between BGP translation and pattern reordering, since both need to run before the topological-ordering step Phase 2 already performs.
- Tier 4 and Tier 5 items should be written into the transpiler's rejection layer from day one with the specific reasoning above (not a generic "unsupported"), so a user hitting one of them understands *why* — especially for `SERVICE`/`CONSTRUCT`/`DESCRIBE`/Update, where the honest answer is "use this other, better-fitted HGAI mechanism instead," not "not implemented yet."

## Recommendation

Build the three Tier 1 gaps into v1 proper — they're common enough, and (per the transpiler-side computation strategy) cheap and safe enough, that deferring them would leave the converter noticeably less useful for a modest amount of extra work. Treat Tier 2 as stretch goals worth picking up if v1's schedule allows, since they're similarly cheap but less frequently needed. Ship Tier 3 as documented, honest approximations rather than either silently mistranslating them or refusing them outright. Write Tier 4 and Tier 5 into the project's own documentation as explicit, reasoned non-goals — not gaps waiting to be closed — so nobody re-litigates "why doesn't this support `SERVICE`" as a bug report six months from now.
