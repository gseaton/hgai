# Mutation Summary

## Intent
Phase 3: expose `sum`/`avg`/`min`/`max` in SHQL's `aggregate:` block (storage already supported them) and update the SPARQL conversion plan to use them instead of client-side computation.

## Context
Phase 2 pushed `count`/`group_by` down to storage for single-pattern queries. The SPARQL docs assumed aggregates beyond COUNT would be computed by the (unbuilt) transpiler over capped fetches.

## What Changed and Why
Syntax mirrors `group_by`: each measure names a projected row key (string or list). Results go into `meta` as `{fn: {row_key: value}}`, plus `group_measures` per group beside the unchanged `groups`. Eligible single-pattern queries are computed by `store.aggregate` (a global call plus, with `group_by`, one grouped call); everything else uses `_aggregate_in_memory`, which reduces rows with the storage layer's own `reduce_values`, so both paths agree by construction and tests confirm it against reference and real MongoDB. The SPARQL docs now say the transpiler emits `aggregate:` (with `limit: 0` for aggregate-only queries) and must relay `meta.truncated` for non-pushed-down results.

## Key Decisions
- New meta keys rather than changing `groups` (backward compatible).
- Row keys without `?`, validated in the parser, since a `?` key silently matches nothing.
- If two distinct group values collide after `str()` and measures are requested, pushdown bails out to the in-memory path (avg cannot be merged exactly).
- `tags` measures/groups stay in-memory (array semantics differ between paths).
- Documented that SUM/AVG differ from SPARQL (ignore non-numerics; empty AVG is null).
- The transpiler itself is still unwritten; only the plan documents changed.
