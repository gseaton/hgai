# Mutation Log

## Modified
- **docs/design/epics-to-build-production-hgai/build-plan.md** — Expanded §6.2 (SHQL spec). Added: (1) an explicit statement that query results are binding tables (`{?var: resolved_value, ...}` rows, one per satisfying assignment — SPARQL `SELECT`-style), not a flat list of matched entities; (2) a statement that any `?var` bound by any pattern (node, edge, or a `members:` sub-pattern) at any hop is addressable by dot-path (`?var.field`, `?var.attributes.nested.path`) in both `select:` and `filter:`; (3) a statement that multi-hop chaining is anchor reuse (a later pattern referencing an already-bound `?var`), not a dedicated path/traverse operator; (4) a worked two-hop YAML example selecting an attribute from the hop-2 binding.
