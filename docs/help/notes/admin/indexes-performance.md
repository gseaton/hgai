---
id: help-indexes-performance
label: Indexes and performance
name: indexes-performance
description: MongoDB indexes created at startup, the query cache and its graph-scoped invalidation, and concurrent mesh fan-out.
tags: ["//Administration", performance, indexes, cache, mongodb]
status: active
---

# Indexes and performance

## MongoDB indexes

Indexes are created automatically at startup (`ensure_indexes()`); the call is idempotent. Highlights:

| Collection | Notable indexes |
|---|---|
| `hypergraphs` | unique `id`; `status` |
| `hypernodes` | unique `(id, hypergraph_id)`; `(hypergraph_id, status)`; `(hypergraph_id, type)`; `tags`; `label`; sparse `(hypergraph_id, valid_from, valid_to)` for [PIT](help:help-point-in-time) |
| `hyperedges` | unique `(id, hypergraph_id)`; unique `(hyperkey, hypergraph_id)` (semantic de-duplication); `(hypergraph_id, relation)`; multikey `members.node_id`; sparse PIT index |
| `meshes`, `accounts` | unique `id` / `username` |
| `query_cache` | unique `cache_key`; multikey `graph_ids`; TTL on `expires_at` |
| `audit_log` | `timestamp` descending |

Verify with `mongosh`: `use hgai` then `db.hypernodes.getIndexes()`.

## Query cache

SHQL results are cached (`HGAI_CACHE_ENABLED`, `HGAI_CACHE_TTL_SECONDS`). Each entry records the local graph ids it queried, so a write to graph `X` evicts only entries that touched `X` — other graphs' cached results stay valid. Creating, updating or deleting a *hypergraph* flushes the whole cache. Entries for fully remote (mesh) graphs can't be tracked locally and simply expire via the TTL. The **System** screen has a Query Cache panel; you can also flush it by calling `POST /api/v1/shql/cache/invalidate`.

## Concurrent mesh fan-out

Mesh operations (ping, sync, federated queries, dot-notation refs) use `asyncio.gather`, so total time is roughly the slowest server. A failing server does not cancel the others. Outbound HTTP shares one pooled `httpx.AsyncClient` (100 connections, 20 keep-alive, 30 s keep-alive expiry, 10 s timeout). See [Meshes](help:help-meshes).
