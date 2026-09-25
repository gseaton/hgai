# Mutation Log

## Modified
- **hgai_module_storage/aggregate.py** — Factored per-value folding into `_feed_value`/`_final_value`; added public `reduce_values(fn, values)` so in-memory callers share storage semantics.
- **hgai_module_shql/parser.py** — Added `_validate_aggregate` (sum/avg/min/max take a row key or list; no leading `?`; block must be a mapping), called from `validate_shql`.
- **hgai_module_shql/engine.py** — `aggregate:` gains `sum`/`avg`/`min`/`max`: new `_aggregate_in_memory`, `_measure_requests`, `_shape_measures`; planner/runner generalised (`_pushdown_field`, measures in `_AggregatePlan`, global + per-group storage calls, `None` on str-key collision with measures); meta gains `sum`/`avg`/`min`/`max` and `group_measures`.
- **tests/test_shql_aggregate_pushdown.py** — Equivalence cases for measures, value/empty-match/cap tests, collision test, aggregate validation tests, extra fallbacks.
- **tests/test_storage_aggregate.py** — `reduce_values` vs `Accumulator` agreement test.
- **docs/help/notes/shql/shql-advanced.md**, **shql-overview.md** — Documented measures, `group_measures`, semantics.
- **docs/architecture/sparql-to-shql-conversion-plan.md**, **docs/architecture/sparql-vs-shql-gaps.md** — Aggregates now map to SHQL `aggregate:` (pushdown when eligible); removed the transpiler-side client-side SUM/AVG/MIN/MAX approach; documented semantic differences and `meta.truncated` handling.
