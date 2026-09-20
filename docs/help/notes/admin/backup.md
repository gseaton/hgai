---
id: help-backup
label: Backup and restore
name: backup
description: Back up and restore the HypergraphAI MongoDB database.
tags: ["//Administration", backup, restore, mongodump, mongodb]
status: active
---

# Backup and restore

All HypergraphAI data lives in MongoDB, so backing up the database backs up everything (hypergraphs, nodes, edges, accounts, notes, media metadata, meshes).

```bash
# Backup
docker-compose exec mongo mongodump \
  --username admin --password pwd357 \
  --authenticationDatabase admin \
  --db hgai --out /backup

# Restore
docker-compose exec mongo mongorestore \
  --username admin --password pwd357 \
  --authenticationDatabase admin \
  --db hgai /backup/hgai
```

Adjust credentials, database name (`HGAI_MONGO_DB`) and paths for your deployment, and keep backups somewhere that survives `docker-compose down -v` ([Docker](help:help-docker)). A single hypergraph can also be saved to a portable file and imported into any instance — see [Exporting and importing hypergraphs](help:help-export-import).
