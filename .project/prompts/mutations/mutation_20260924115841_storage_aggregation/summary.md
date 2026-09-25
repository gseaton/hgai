# Mutation Summary

## Intent
Phase 1 of pushing aggregation into the storage layer (so SHQL can stop reducing millions of documents in Python): a backend-neutral contract, a default implementation for any backend, and a MongoDB pushdown.

## Context
Follows an ask that proposed the design; the user chose adding `aggregate`/`count` as new methods on the existing node and edge stores. SHQL itself is not changed yet (phase 2).

## What Changed and Why
`AggregateSpec`/`AggregateMeasure` describe group-by fields, measures, ordering and limit. `hgai_module_storage/aggregate.py` is the single statement of semantics and holds a streaming reducer; the ABCs' default `aggregate` pages through `search` into it, so every backend (including third-party) is correct immediately. `MongoHypernodeStore`/`MongoHyperedgeStore` override it with a pipeline built in `hgai_module_storage_mongodb/aggregation.py`, sharing a `_build_search_query` extracted from `search` so filters cannot drift between the two paths. A conformance suite runs identical assertions against the reference and a real `mongod`.

## Key Decisions
- Non-abstract methods + capability flag, so existing backends don't break.
- Field paths are whitelisted and pipeline uses internal `g<i>`/`m<i>` names, so user strings never become Mongo field names or operators.
- Semantics choices made explicit so backends agree: `tags` unwound, missing == null, sum/avg ignore non-numbers and bools, min/max use BSON type order, no group_by always returns one row (Mongo's empty result is patched).
- No new indexes added in phase 1; existing `graph_type`/`graph_relation` indexes cover the common group-bys.
