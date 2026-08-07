# Response Summary

## Question / Intent
The user wanted a research-only survey (explicitly no code changes) of the possible approaches to implementing semantic inferencing in HypergraphAI, covering many options with trade-offs, pros, and cons — to inform a future implementation decision, not to commit to one now.

## Answer / Recommendation

### Current state (verified against code, not just docs)
- `hgai/core/inference.py` (`infer_inverse_edges`, `check_transitive_relation`) is **entirely dead code** — zero call sites anywhere in the codebase (no API router, no HQL/SHQL engine, no MCP tool references it).
- `HyperedgeBase.skos_broader/narrower/related` fields exist on the model but are **actively stripped** (`_SKOS_FIELDS` popped) from every HQL and SHQL query result before returning — readable via raw REST CRUD only.
- A prior implementation was removed in commit `fd56ec4` ("removed flawed use of skos broader and narrow as a hypernode attribute") — it stored SKOS closures as attribute lists on hypernodes and computed closure via a per-item, per-BFS-level Mongo query with no caching, no PIT-awareness, and no query-language surface. Real lesson: putting relationship data on node attributes fights the platform's "hyperedges are first-class" design principle.
- The intended direction is already sketched: `docs/dev_notes/skhg-inferencing-notes.md` describes relation semantics (`owl:transitive`, `owl:symmetric`, `owl:inverse-of`) declared as hypergraph *data* (RelationType hypernodes + axiom hyperedges), and `README.md`'s Inferencing → Roadmap section lists six planned-but-unbuilt capabilities.
- Existing reusable infrastructure: `hgai/core/cache.py`'s graph-scoped cache invalidation (already wired into every mutation in `hgai/core/engine.py`); `TransitiveSearchFilter`/`find_for_transitive` (a per-depth-level batched Mongo query, already better than naive per-node fetches).
- A real functional gap regardless of chosen option: no transitive-walk code threads a `pit` (point-in-time) parameter — a BFS inside a query with `at: <date>` would still walk *current* edge state.

### Cross-cutting design axes (apply to every option, decide before picking one)
- **A. Where rules live**: data-declared (RelationType hypernodes/axiom hyperedges) vs. code-declared (Python rule registry) vs. hybrid (fixed rule shapes in code, parameterized by relation-type data — closest to what `infer_inverse_edges`'s `attributes.inverse` already half-does).
- **B. When computed**: on-demand (always fresh, no write cost, repeated read cost) vs. materialized (zero read cost, write amplification + GC problem on source deletion) vs. cached (middle ground, but breaks for PIT queries which must always bypass the cache).
- **C. Query-language surface**: always-on (implicit, surprising) vs. explicit opt-in (matches the existing `_inferred`/`_source_edge` convention; the roadmap's own suggested `infer:` clause).
- **D. Scope**: single-graph vs. logical-composition vs. mesh-spanning (mesh inference is a different cost model — remote HTTP hops instead of local queries — and should be a separate design phase).

### Options surveyed (six), each with pros/cons
1. **Wire up what already exists** (`infer_inverse_edges` + a closure-returning transitive walk, behind an explicit `infer:` directive). Lowest risk/effort, ships the README's already-documented (but non-functional) inverse-edge and transitive-reachability features. Needs extension from yes/no reachability to actual closure, and needs PIT threading added.
2. **Declarative relation-type inference** (the dev-notes vision: axioms as data on RelationType hypernodes). Matches the codebase's own documented direction; new relations "just work" without code changes. Needs a rule-interpretation layer and provenance/consistency validation that doesn't exist today.
3. **Materialized/cached closures** reusing `query_cache`'s graph-scoped invalidation pattern. Fast reads for hot paths, low invalidation risk (reuses existing mechanism). Fundamentally incompatible with PIT queries (must always bypass); classic closure-size blowup risk on dense transitive relations.
4. **MongoDB `$graphLookup`** for native single-round-trip traversal. Fast, well-tested Mongo feature. `$graphLookup` is binary-edge-oriented, not n-ary — needs a denormalized edge-pairs collection or flavor-restriction; ties inferencing to MongoDB specifically, undermining the `hgai_module_storage` backend-registry abstraction.
5. **Rule-based inference engine** as a new pluggable module (`hgai_module_inference`), rules as `InferenceRule` hypernodes, forward- or backward-chaining. Most general — subsumes the other options as special cases, satisfies four of six roadmap items at once. By far the highest complexity: cycle detection, termination guarantees, materialized-inferred-edge GC/dedup-index conflicts, and a whole new rule-authoring UX surface.
6. **External reasoner integration** (embedded Datalog/OWL library, or export-to-RDF-and-reason). Avoids reinventing reasoning correctness. Heavy new dependency inconsistent with the project's lean footprint; n-ary→RDF triple translation is lossy (reification problem); round-trip latency likely too slow for interactive queries; most such libraries are class-heavy, sitting awkwardly against this project's `no_classes_rule.md`. Not recommended for this codebase.

### Recommended sequencing
1. Option 1 first (ship something real, battle-test the `_inferred` convention, add PIT threading while touching that code).
2. Option 2 next (move semantics onto RelationType data — where the codebase's own design notes already point).
3. Option 3 only once a hot path is actually measured (not speculative), always bypassed for PIT queries.
4. Option 5 only if rule-based inference becomes an actual product requirement — right long-term ceiling, wrong starting floor.
5. Option 4 opportunistically and backend-specific, only after profiling shows the Python BFS is the real bottleneck.
6. Option 6 skipped unless requirements genuinely outgrow OWL-lite property chains into full OWL-DL.
Cross-graph/mesh inferencing (roadmap item #4) deliberately deferred out of scope for all options above — different cost model, deserves its own design pass.

## Key Points
- This was framed and treated as research-only per explicit user instruction — no files under `hgai/`, `hgai_module_*`, `ui/`, or `README.md` were modified in this turn.
- The six options are not mutually exclusive alternatives so much as points on the four cross-cutting axes (A–D); the recommended sequencing treats them as incremental layers rather than a single either/or choice.
- Two concrete, verified defects were surfaced that apply no matter which option is chosen: (1) zero PIT-awareness in any existing transitive-walk code, (2) the historical node-attribute approach was already tried and removed for fighting the "hyperedges are first-class" principle — any new design should avoid repeating that specific mistake.

## Context
Grounded directly in repository state: `hgai/core/inference.py`, `hgai/models/hyperedge.py`, `hgai_module_hql/engine.py` / `hgai_module_shql/engine.py` (`_SKOS_FIELDS` stripping), `hgai/core/cache.py`, `hgai_module_storage_mongodb/stores/hyperedges.py` (`find_for_transitive`), `hgai_module_storage/registry.py` (backend-pluggability constraint), `docs/dev_notes/skhg-inferencing-notes.md`, `README.md`'s Inferencing/Roadmap section, and git history commit `fd56ec4` (the removed prior SKOS-on-hypernode-attributes implementation). No code was modified as part of producing this research.
