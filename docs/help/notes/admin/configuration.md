---
id: help-configuration
label: Configuration
name: configuration
description: Environment variables and .env settings for the server — storage, secrets, ports, caching, server identity.
tags: ["//Administration", config, environment, settings, env]
status: active
---

# Configuration

All configuration is through environment variables (prefix `HGAI_`) or a `.env` file. Copy `.env.example` to `.env` to start.

| Variable | Default | Description |
|---|---|---|
| `HGAI_STORAGE_BACKEND` | `mongodb` | Storage backend (MongoDB is the only built-in one) |
| `HGAI_MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection URI |
| `HGAI_MONGO_DB` | `hgai` | MongoDB database name |
| `HGAI_SECRET_KEY` | *(required)* | Secret used to sign JWTs (and to encrypt stored AI vendor keys) |
| `HGAI_TOKEN_EXPIRE_MINUTES` | `480` | JWT lifetime |
| `HGAI_PRIMARY_API_KEY` | *(none)* | Machine-to-machine API key ([Authentication](help:help-authentication)) |
| `HGAI_SECONDARY_API_KEY` | *(none)* | Second key for rotation |
| `HGAI_HOST` | `0.0.0.0` | Bind host |
| `HGAI_PORT` | `8357` | Bind port |
| `HGAI_LOG_LEVEL` | `info` | Log level |
| `HGAI_CACHE_ENABLED` | `true` | Enable the query-result cache |
| `HGAI_CACHE_TTL_SECONDS` | `300` | Cache time-to-live |
| `HGAI_SHQL_MAX_NODE_CANDIDATES` | `2000` | Max hypernodes fetched per SHQL `node:` pattern; overflow sets `meta.truncated` |
| `HGAI_SHQL_MAX_EDGE_CANDIDATES` | `2000` | Max hyperedges fetched per SHQL `edge:` pattern; overflow sets `meta.truncated` |
| `HGAI_INFERENCE_MAX_FACT_EDGES` | `5000` | Max fact edges fetched for inference expansion / transitive closure |
| `HGAI_SHQL_JOIN_BATCH_SIZE` | `200` | Max distinct bound values (node ids / member-id sets) resolved per storage query when a SHQL pattern joins against many earlier matches; `1` = one query per match |
| `HGAI_TELEMETRY_ENABLED` | `false` | Master switch for OTEL-shaped usage/error telemetry (off by default) |
| `HGAI_TELEMETRY_ENDPOINT` | *(none)* | URL telemetry batches are POSTed to, e.g. `https://telemetry.hypergra.ai/report`; optional even when enabled |
| `HGAI_TELEMETRY_PROTOCOL` | `hgai-envelope` | Wire format for the endpoint above (`otlp-http-json` not yet implemented) |
| `HGAI_TELEMETRY_API_KEY` | *(none)* | Optional bearer credential sent to the telemetry endpoint |
| `HGAI_TELEMETRY_BATCH_SIZE` | `100` | Max events per export batch |
| `HGAI_TELEMETRY_FLUSH_INTERVAL_SECONDS` | `10` | Max time an event waits before its batch is dispatched |
| `HGAI_TELEMETRY_QUEUE_MAX_SIZE` | `10000` | Bounded in-memory event queue; oldest event dropped when full |
| `HGAI_TELEMETRY_LOCAL_ENABLED` | `false` | Also write to the `__local-telemetry` hypergraph even when an endpoint is set (always used when no endpoint is set, regardless of this flag) |
| `HGAI_TELEMETRY_LOCAL_RETENTION_DAYS` | `30` | Prune `__local-telemetry` hypernodes older than this many days; `0` disables pruning |
| `HGAI_TELEMETRY_INCLUDE_GRAPH_IDS` | `false` | Send graph/space ids in the clear instead of HMAC-hashed |
| `HGAI_TELEMETRY_INCLUDE_ACCOUNT_IDS` | `false` | Send account usernames in the clear instead of HMAC-hashed |
| `HGAI_TELEMETRY_ALLOW_INSECURE` | `false` | Permit a non-HTTPS telemetry endpoint (local development only) |
| `HGAI_TELEMETRY_SAMPLE_RATE` | `1.0` | Fraction of *usage* events kept (0.0-1.0); errors are never sampled |
| `HGAI_TELEMETRY_ENVIRONMENT` | `production` | Free-text `deployment.environment` resource attribute |
| `HGAI_SERVER_ID` | `hgai-local` | Server identifier (used in [meshes](help:help-meshes)) |
| `HGAI_SERVER_NAME` | `HypergraphAI Local` | Server display name |
| `HGAI_HELP_DIR` | `<project>/docs/help` | Root of the built-in Help content ([Adding help topics](help:help-authoring-help)) |

The `HGAI_TELEMETRY_*` settings above are covered in full, including exactly what is and isn't collected, in [Telemetry](help:help-telemetry).

Command-line options of `./hgai.sh` (`--port`, `--mongo-db`, `--server-id`, `--server-name`) override the environment — see [Running locally](help:help-running-locally).

## Storage backends

All storage access goes through an abstract interface in `hgai_module_storage`; no other module talks to MongoDB directly. To add a backend, implement `StorageBackend` and the per-entity stores, call `register_backend("myname", MyBackend)` on import, and set `HGAI_STORAGE_BACKEND=myname`.

## Security checklist

- Set a long random `HGAI_SECRET_KEY`.
- Change the default `admin` password ([Accounts and roles](help:help-accounts-roles)).
- Treat API keys as admin credentials.
