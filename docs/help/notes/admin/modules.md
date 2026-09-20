---
id: help-modules
label: Modules
name: modules
description: HypergraphAI's pluggable module architecture and how to write your own.
tags: ["//Administration", modules, extension, plugin, development]
status: active
---

# Modules

Every subsystem is a module named `hgai_module_<name>/`. Built in: `hgai_module_storage` and `hgai_module_storage_mongodb` (storage), `hgai_module_shql` ([SHQL](help:help-shql-overview)), `hgai_module_mesh` ([meshes](help:help-meshes)), `hgai_module_mcp` ([MCP](help:help-mcp-server)) and `hgai_module_agentchat` ([AI Chat](help:help-ai-chat)).

Modules are mounted conditionally in `hgai/main.py`: a missing or broken module logs a warning and is skipped, and the server keeps running.

## Minimal module

```
hgai_module_mymodule/
├── __init__.py        # exports MyModule
├── module.py          # class with name/version/description and get_router() or get_app()
└── api_router.py      # FastAPI router (optional)
```

A module returns a FastAPI `APIRouter` from `get_router()` (REST) or an ASGI app from `get_app()` (mounted, like MCP). Register it in `hgai/main.py`.

The full guide is `docs/module-development.md`.
