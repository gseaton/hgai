# Mutation Log

## Created
- **hgai_module_storage/aggregate.py** — Backend-neutral aggregation semantics: field-path whitelist, `normalise_spec`, BSON-like `sort_key`, streaming `Accumulator`, and `aggregate_via_search` (paged reference implementation).
- **hgai_module_storage_mongodb/aggregation.py** — `run_aggregate`: translates an `AggregateSpec` to a Mongo pipeline (`$match`/`$unwind`/`$group`/`$set`/`$sort`/`$limit`) and maps rows back.
- **tests/test_storage_aggregate.py** — Conformance suite run against a reference in-memory store and a real throwaway `mongod`; also spec-validation and paging tests.

## Modified
- **hgai_module_storage/filters.py** — Added `AGGREGATE_FUNCTIONS`, `AggregateMeasure`, `AggregateSpec`.
- **hgai_module_storage/backend.py** — `HypernodeStore` and `HyperedgeStore` gain non-abstract `aggregate`, `count`, and `supports_aggregate_pushdown = False`.
- **hgai_module_storage_mongodb/stores/hypernodes.py**, **hyperedges.py** — Extracted `_build_search_query` from `search` (behaviour unchanged) and added `aggregate` pushdown override plus `supports_aggregate_pushdown = True`.
- **docs/module-development.md** — Added "Aggregation" section for module and backend authors.
