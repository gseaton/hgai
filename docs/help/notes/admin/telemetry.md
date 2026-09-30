---
id: help-telemetry
label: Telemetry
name: telemetry
description: What usage and error telemetry collects, what it never collects, where it goes (an external endpoint, the local __local-telemetry hypergraph, or both), and how to turn it on.
tags: ["//Administration", telemetry, privacy, otel, monitoring]
status: active
---

# Telemetry

Telemetry reports **usage** (which feature was used, how long it took, by which account) and **error** (what broke, where, for whom) events — for hot-spot, most-/least-used-feature, per-account and error/bug-report analysis. It is **off by default**. Read this page before turning it on: it says exactly what is and isn't collected, which matters most if HypergraphAI is running somewhere self-hosted and regulated.

## Off by default, on purpose

`HGAI_TELEMETRY_ENABLED=false` out of the box. Turning it on is an explicit operator decision — nothing is collected, queued or sent until you set it to `true`.

## What is collected

Every request (REST), query (SHQL), tool call (MCP), tracked Web UI action and hgsh shell command produces one event:

| Field | What it holds |
|---|---|
| `kind` | `usage` or `error` |
| `surface` | `rest`, `shql`, `mcp`, `web-ui`, or `shell` |
| `feature` | *What* got used — always a template, e.g. `POST /api/v1/hyperedges/{edge_id}`, `mcp.hgai_query_execute`, `ui.visualize.focus_dblclick`, `shell.import-rdf` — never a value like an actual graph or record id |
| `duration_ms` | How long it took |
| `outcome` | `ok`, `denied`, or `error` |
| `actor` | Who acted: the same (hashed) account id as below, or `__system` when no account acted (background or unauthenticated activity) |
| `account` | The caller's roles, whether it's an agent account, and a **hashed** account id (see below) — or nothing, for an unauthenticated request |
| `attributes` | A small, fixed set of extra fields for that surface — e.g. an HTTP status code, or (for SHQL) whether the query used `infer:`, was aggregated, was exact or candidate-capped |
| `error` | Present only on `kind: error`: an exception type, a **templatized** message (see below), a fingerprint for grouping repeats of the same bug, and (where one exists) a repo-relative stack trace — file, line and function only |

## What is never collected

Regardless of any setting:

- Query text, SHQL patterns, or the values inside them
- Hypernode / hyperedge / note content — labels, descriptions, attribute values
- HgNexus chat prompts or completions
- Media file contents or filenames
- Vendor API keys (already encrypted at rest and never touched by telemetry)

Error messages are also **templatized** before they're recorded: quoted text inside a message is replaced with `'…'`, so `Hypergraph not found: 'my-project'` becomes `Hypergraph not found: '…'` — the same underlying bug fingerprints identically across different customers' data instead of leaking what triggered it.

## Account, graph and space ids

An account id is never sent as the plain username. By default it's HMAC-hashed with this server's own secret key, so events can be grouped per account **within this deployment** without being reversible or comparable to any other deployment's data. `HGAI_TELEMETRY_INCLUDE_ACCOUNT_IDS=true` sends it in the clear instead — useful for your own dashboard against your own data, wrong for a shared or externally-reviewed default. `HGAI_TELEMETRY_INCLUDE_GRAPH_IDS` does the same for graph and space ids. Role (`admin`/`user`/…) and whether the account is an agent travel in the clear either way — useful, and not identifying on their own.

## Where it goes

| Setting | Destination |
|---|---|
| No `HGAI_TELEMETRY_ENDPOINT` set | The `__local-telemetry` hypergraph, in this server's own database — nothing leaves the server. |
| `HGAI_TELEMETRY_ENDPOINT` set | That URL, as a single JSON batch per POST. |
| An endpoint set **and** `HGAI_TELEMETRY_LOCAL_ENABLED=true` | Both — independently, so one failing never blocks or duplicates the other. |

An endpoint is only ever used if it's `https://` (or `HGAI_TELEMETRY_ALLOW_INSECURE=true` for local development); otherwise it's treated the same as no endpoint. The **Telemetry** screen (admin) shows exactly which destination(s) are active right now, along with queue depth and the last export's outcome — see [Configuration](help:help-configuration) for the full settings table.

## Local storage: `__local-telemetry`

When events are stored locally, each one becomes an ordinary hypernode (`type: OTEL`) in a hypergraph called `__local-telemetry` — the same way every other hypernode is stored, so it's queryable with [SHQL](help:help-shql-overview) immediately, no separate dashboard needed. From the **Telemetry** admin screen, **Browse local telemetry in Query (SHQL)** opens a starter query. A quick example, most-used features this week:

```yaml
shql:
  from: __local-telemetry
  where:
    - node: {bind: '?n', type: OTEL}
  select: ['?n.attributes.feature']
  aggregate:
    count: true
    group_by: n.attributes.feature
```

`__local-telemetry` doesn't show up in the ordinary Hypergraphs list (id prefix `__` is reserved for platform-internal graphs) and is never included in [mesh](help:help-meshes) federation's "every graph on this server" fan-out — federating it would leak this server's own usage data to another server. It's reachable directly by id (`GET /api/v1/graphs/__local-telemetry`, or in SHQL's `from:`) for an admin, the same way any other unowned graph is: nothing outside the `admin` role can see it, using the platform's ordinary permission model — no special case.

Hypernodes older than `HGAI_TELEMETRY_LOCAL_RETENTION_DAYS` (default 30) are pruned automatically, about once an hour. Set it to `0` to keep everything.

## Turning it on

1. Set `HGAI_TELEMETRY_ENABLED=true`.
2. Either leave `HGAI_TELEMETRY_ENDPOINT` unset (local storage only) or point it at a collector.
3. Restart the server.
4. Check the **Telemetry** admin screen, or `GET /api/v1/telemetry/status` (admin-only), to confirm it's running and see where it's sending data.

See [Configuration](help:help-configuration) for every `HGAI_TELEMETRY_*` setting.
