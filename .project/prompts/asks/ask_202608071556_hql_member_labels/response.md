# Response Summary

## Question / Intent
The user wanted to know whether a single HQL query on a hyperedge can return the `label`/`attributes` of its member hypernodes, rather than just the raw `members` array (`node_id`/`seq` pairs).

## Answer / Recommendation
**No — not in a single HQL query.** Verified live against a disposable server: HQL only ever searches one collection at a time (hypernodes *or* hyperedges via `match.type`), with no cross-collection join. A returned hyperedge's `members` field is always bare `{node_id, seq}` regardless of what's listed in `return:`.

Two real paths forward:
1. **A second HQL query** — but `where: {id: {$in: [...]}}` against hypernodes silently returns zero rows (the same "unrecognized `where` key gets folded into `attributes.<key>`" bug that also breaks `$or` on hypernode queries — see prior ask on 2026-07-31). `match.id` only supports one literal id at a time, so bulk-fetching several specific member nodes via HQL is awkward (one query per id, or fetch a broader set and cross-reference client-side).
2. **SHQL** — the correct built-in tool for this. Anchor the edge by `relation` (+ a known member if available) and add an unconstrained member sub-pattern to expand every other member, then `select: ?member.label` / `?member.attributes` directly. Example given using the user's own `rel:member`/`group:three-stooges` naming (from their open `notes/queries.md` selection):
   ```yaml
   shql:
     from: hello-world
     select:
       - ?member.id
       - ?member.label
       - ?member.attributes
     where:
       - edge:
           relation: "rel:member"
           members:
             - node: { id: "group:three-stooges" }
             - node: { bind: "?member" }
   ```

## Key Points
- A second, unprompted finding surfaced while verifying: SHQL `edge:` patterns silently ignore a literal `id:` key entirely (`_eval_edge_pattern` never reads `id` — only `bind`/`relation`/`flavor`/`tags`/`attributes`/`members`/`status`). Tested `edge: { id: some-edge-id, members: [...] }` directly — it matched every edge in the graph, not just the named one. Edges must be filtered by `relation` (+ optionally `flavor`/`tags`/`attributes`/known members), never by `id`.
- Both findings were saved to memory (`hgai_shql_hql_engine_quirks.md`) since they're non-obvious, verified-live engine limitations likely to recur in future query-writing work on this project.

## Context
Verified by spinning up a disposable throwaway HypergraphAI server (`hgai_demo_validate3`, port 8399), seeding it with the existing `docs/decks/demo-alpha/data/acme-eng-import.yaml` dataset, and running four targeted HQL/SHQL queries against the real engine before answering — consistent with the verification approach used throughout this conversation. Server and its MongoDB database were torn down immediately after. No project files were modified; only external memory notes were updated.
