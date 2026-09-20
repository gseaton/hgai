---
id: help-docker
label: Docker deployment
name: docker
description: Build, run, monitor, stop and reset HypergraphAI with Docker Compose.
tags: ["//Administration", docker, compose, deployment]
status: active
---

# Docker deployment

```bash
cp .env.example .env
docker-compose up --build -d          # build and run MongoDB + the server
docker-compose logs -f hgai           # follow the server log
docker-compose exec hgai python scripts/seed_data.py   # optional sample data
docker-compose down                   # stop
docker-compose down -v                # stop AND delete all data (volumes)
```

`docker-compose down -v` **deletes your data**. Take a [backup](help:help-backup) first.

Under Compose the server listens on **port 8000**:

- Web UI `http://localhost:8000/ui/`
- API docs `http://localhost:8000/api/docs`
- MCP `http://localhost:8000/mcp/`
- Health check `http://localhost:8000/health`

The image includes the built-in Help content, so this Help tab works in containers too. Settings are passed as environment variables — see [Configuration](help:help-configuration).
