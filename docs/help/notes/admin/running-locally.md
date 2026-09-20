---
id: help-running-locally
label: Running locally
name: running-locally
description: Start the server for development, choose ports and databases, and run several servers side by side.
tags: ["//Administration", local, dev, hgai.sh, ports]
status: active
---

# Running locally

```bash
pip install -r requirements.txt

# MongoDB (or use your own instance)
docker run -d -p 27017:27017 --name hgai-mongo \
  -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=pwd357 mongo:7
mongosh --username admin --password pwd357 \
  --authenticationDatabase admin < scripts/mongo-init.js

cp .env.example .env
./hgai.sh                       # http://localhost:8357/ui/
python scripts/seed_data.py     # optional: load the example hypergraphs from scripts/seeds/ (hello-world, eden)
```

## Options

```bash
./hgai.sh                                        # port 8357, database "hgai"
./hgai.sh --port 9000                            # custom port
./hgai.sh --mongo-db mydb --server-id my-server  # full options
```

Environment defaults used when an option is not given: `HGAI_PORT`, `HGAI_MONGO_URI`, `HGAI_MONGO_DB`, `HGAI_SERVER_ID`, `HGAI_SERVER_NAME` ([Configuration](help:help-configuration)).

## Parallel servers (for meshes)

Give each its own port, server id and database:

```bash
./hgai.sh --port 8361 --server-id hgai-alpha --mongo-db hgai_alpha --server-name HypergraphAI-Alpha
./hgai.sh --port 8362 --server-id hgai-bravo --mongo-db hgai_bravo --server-name HypergraphAI-Bravo
```

Then register them in a [mesh](help:help-meshes) to query across them.

## Endpoints

| | URL |
|---|---|
| Web UI | `http://localhost:8357/ui/` |
| API docs | `http://localhost:8357/api/docs` |
| MCP | `http://localhost:8357/mcp/` |

Default login: `admin` / `pwd357` — change it ([Accounts and roles](help:help-accounts-roles)). Running under Docker instead? See [Docker deployment](help:help-docker).
