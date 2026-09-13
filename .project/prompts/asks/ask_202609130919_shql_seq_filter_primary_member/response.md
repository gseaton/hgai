# Response Summary

## Question / Intent
Turn 1 asked for an improved SHQL query isolating the "primary (index 0) member" of `group:three-stooges`. Turn 2 clarified the actual goal: return all members (seq 1+) of the hub-flavored hyperedge where `group:three-stooges` is itself the seq-0 anchor, at a given point-in-time. Turn 3 disputed the Turn 2 answer, reporting that the query doesn't respect the `at:` PIT — specifically that `person:curly-joe` appears in the 1946 result even though that lineup shouldn't be valid then.

## Answer / Recommendation
Final query (unchanged from Turn 2 — the query itself is correct):

```yaml
shql:
  from:
    - hello-world
  at: "1946-01-01T00:00:00"
  where:
    - edge: "?membership"
      relation: "rel:member"
      flavor: "hub"
      members:
        - bind: "?group"
          id: "group:three-stooges"
          seq: 0
        - bind: "?member"
    - node: "?member"
      bind: "?member_node"
  select:
    - "?member_node.id"
    - "?member_node.label"
    - "?member_node.type"
    - "?member_node.attributes"
```

**Turn 3's report is accurate, but the query is not the defect** — the PIT mechanism itself is working correctly and consistently; the surprise is a real, undocumented, system-wide convention: an entity with `valid_from`/`valid_to` both `null` is treated as **unconditionally valid at every point in time**, not excluded from PIT queries. This is implemented in `_pit_clause()` (`hgai_module_storage_mongodb/stores/hyperedges.py`):

```python
def _pit_clause(pit):
    return [
        {"$or": [{"valid_from": None}, {"valid_from": {"$lte": pit}}]},
        {"$or": [{"valid_to": None}, {"valid_to": {"$gte": pit}}]},
    ]
```

`edge:stooges-curly-joe` has `valid_from: null, valid_to: null`, so it satisfies both `$or` clauses at any `pit` value whatsoever.

Two ways forward, presented as a genuine choice rather than picked unilaterally (see Key Points for why):
1. **Data fix**: set real `valid_from`/`valid_to` on `edge:stooges-besser` and `edge:stooges-curly-joe` (the two hub edges with no bounds), matching when Joe Besser and Curly Joe DeRita actually joined the act. Surgical, fixes this query specifically, no risk to anything else.
2. **Behavior change**: flip `_pit_clause`'s null handling so an absent bound *excludes* rather than *includes* an entity from PIT queries. System-wide, affects every PIT query (HQL and SHQL) over every hypernode and hyperedge with unset temporal fields — not proposed as the default recommendation without explicit confirmation.

## Key Points
- **Verified the mechanism is systemic and consistent, not a one-off bug**, by running the same query at three wildly different PITs — 1800-01-01, 1946-01-01, and 2100-01-01 — and confirming `person:curly-joe` appears in *all three*, including 150 years before and after any plausible validity window. If this were a localized PIT-filtering bug (e.g. only applying near 1946, or an off-by-something date comparison error), it would not have shown up identically at three centuries apart.
- **Confirmed the same `_pit_clause` construction is used identically in both `.list()` and `.search()`** (the latter being the specific method SHQL's edge-pattern matching calls via `HyperedgeSearchFilters`) — ruling out the possibility that SHQL's pattern-matching path bypasses PIT filtering while some other path enforces it correctly.
- **Confirmed PIT filtering *does* correctly exclude edges that have real bounds**: `person:curly` (from `edge:classic-stooges`, bounded 1932–1946) appears only in the 1946 result and correctly drops out at both 1800 and 2100 — direct evidence the comparison logic itself is sound, not just "always permissive."
- **`person:moe` himself has `valid_from: null, valid_to: null`** — the same "no recorded bound" state as the disputed `curly-joe` edge. This is why a system-wide flip of the null convention (option 2 above) isn't offered as the obvious fix: it would also make Moe himself stop matching PIT queries with no explicit temporal data, which is likely a much larger, more disruptive change than the user is asking to sign up for over this one query — hence presenting it as an explicit choice rather than just doing it.
- Checked `docs/concepts.md`'s "Temporal Support" section and found no documented convention either way for null `valid_from`/`valid_to` under PIT queries — this is an implementation-level design choice, not something contradicting a written spec, which is part of why it's worth flagging as a decision point rather than treating either option as obviously "the fix."

## Context
Builds on Turns 1–2's investigation of the SHQL engine's edge-pattern matching (`_eval_edge_pattern` in `hgai_module_shql/engine.py`) and member-pattern matching (`_match_members`/`_match_members_expand`). Turn 3's investigation went one level deeper, into the MongoDB storage layer's actual PIT query construction, since the dispute was specifically about whether PIT filtering was being applied at all — verified empirically at multiple PITs rather than re-asserting the Turn 2 explanation unchecked.

## Resolution (Turn 4)
The user chose option 1 (the data fix) and applied it themselves, outside this session's tool calls — no mutation was made by the assistant. Independently re-verified afterward: `edge:stooges-besser` now has `valid_from: 1954-06-16T07:00:00` / `valid_to: 1956-06-16T06:59:00`, and `edge:stooges-curly-joe` now has `valid_from: 1956-06-16T07:01:00` / `valid_to: 1970-01-31T07:59:00` — both matching the real-world dates those two performers actually joined and left the act. Re-ran the Turn 2 query at `1946-01-01T00:00:00` and confirmed it now returns exactly `person:moe`, `person:larry`, `person:curly` — the one historically accurate 1946 lineup, with `curly-joe` and `joe-besser` correctly excluded. Ask thread closed; no further action needed.
