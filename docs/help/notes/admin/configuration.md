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
| `HGAI_SERVER_ID` | `hgai-local` | Server identifier (used in [meshes](help:help-meshes)) |
| `HGAI_SERVER_NAME` | `HypergraphAI Local` | Server display name |
| `HGAI_HELP_DIR` | `<project>/docs/help` | Root of the built-in Help content ([Adding help topics](help:help-authoring-help)) |

Command-line options of `./hgai.sh` (`--port`, `--mongo-db`, `--server-id`, `--server-name`) override the environment — see [Running locally](help:help-running-locally).

## Storage backends

All storage access goes through an abstract interface in `hgai_module_storage`; no other module talks to MongoDB directly. To add a backend, implement `StorageBackend` and the per-entity stores, call `register_backend("myname", MyBackend)` on import, and set `HGAI_STORAGE_BACKEND=myname`.

## Security checklist

- Set a long random `HGAI_SECRET_KEY`.
- Change the default `admin` password ([Accounts and roles](help:help-accounts-roles)).
- Treat API keys as admin credentials.
