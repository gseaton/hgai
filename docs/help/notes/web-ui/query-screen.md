---
id: help-query-screen
label: Query (SHQL) screen
name: query-screen
description: Write, validate and run SHQL queries in the Web UI, with examples, history and cached results.
tags: ["//Using the Web UI", shql, query, editor]
status: active
---

# Query (SHQL) screen

The **Query (SHQL)** screen is an editor for [SHQL](help:help-shql-overview) — YAML queries whose top-level key is `shql:`.

## Toolbar

- **Examples** — insert one of the built-in sample queries.
- **History** — reopen a query you ran earlier.
- **Parameterized** — pick a saved [parameterized query](help:help-parameterized-queries), fill its parameters, and run it.
- **Validate** — check the query without executing it (a dry run).
- **Run** — execute it and show the results.
- **Cache** — toggle use of the query-result cache (on by default).
- **Copy** — copy the results.

## Tips

- Start with `from:` (a graph id, `space/graph`, a list of them, or a [mesh](help:help-meshes) reference) and one `where:` pattern, then add patterns and a `select:`.
- Results are limited to 500 rows unless you set `limit:`.
- Each `node:`/`edge:` pattern reads at most a configurable number of candidates (default 2,000; see [Configuration](help:help-configuration)). If a pattern hits that cap, the result's `meta.truncated` is `true` and `meta.truncated_by` says which pattern — `items` then cover only the fetched candidates (unless `meta.paging_pushdown` is `true`, when storage sorted and paged the rows exactly), and so do aggregates unless `meta.aggregate_pushdown` is `true` (see [aggregation](help:help-shql-advanced)).
- Use **Validate** first to catch syntax problems without running anything.

The same query can be run through the API (`POST /api/v1/shql/query`) or MCP (`hgai_query_execute`). Learn the language in [SHQL overview](help:help-shql-overview) and the [worked examples](help:help-shql-examples).
