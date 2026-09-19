"""HypergraphAI FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager, AsyncExitStack
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from hgai.config import get_settings
from hgai.db.storage import init_storage, close_storage
from hgai.core.auth import bootstrap_admin
from hgai.api.routers import auth, hypergraphs, hypernodes, hyperedges, accounts, spaces, media, inference, notes, parameterized_queries

logger = logging.getLogger(__name__)

_mcp_module = None  # set by create_app(), consumed by lifespan


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles that forces browsers to revalidate on every load.

    This project ships plain, non-hashed filenames for ui/js/*.js and
    ui/css/*.css (no build step, no cache-busted asset names), so a browser
    left to its own heuristic freshness (the default when no Cache-Control
    header is sent at all) can silently keep serving a stale copy after a
    deploy until the user does a hard refresh — confusing during
    development and equally confusing for an end user who "isn't seeing"
    a shipped fix. `no-cache` (not `no-store`) is the right header for
    this: it still allows the browser to cache the file and revalidate
    with a cheap conditional request (StaticFiles already sets ETag/
    Last-Modified, so an unchanged file gets a 304 with no body), it just
    forbids serving that cached copy without checking first.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting HypergraphAI server: {settings.server_name} ({settings.server_id})")

    # Connect to storage backend
    await init_storage(
        settings.storage_backend,
        mongo_uri=settings.mongo_uri,
        mongo_db=settings.mongo_db,
    )
    logger.info(f"Storage backend '{settings.storage_backend}' connected (db: {settings.mongo_db})")
    print(f"Storage backend: {settings.storage_backend}, database: {settings.mongo_db}")

    # Bootstrap admin account on first run
    created = await bootstrap_admin(
        username=settings.admin_username,
        password=settings.admin_password,
        email=settings.admin_email,
    )
    if created:
        logger.info(f"Admin account '{settings.admin_username}' created (first run bootstrap)")

    # Start mesh background sync scheduler
    try:
        from hgai_module_mesh.scheduler import start_scheduler, stop_scheduler
        start_scheduler(settings.mesh_sync_interval_seconds)
    except ImportError:
        stop_scheduler = None

    # Seed the default AI Agent vendor/model catalog on first run
    if settings.agent_chat_enabled:
        try:
            from hgai_module_agentchat.store import seed_defaults
            await seed_defaults()
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"AI Agent catalog seeding failed (continuing without it): {type(e).__name__}: {e}")

    async with AsyncExitStack() as stack:
        if _mcp_module is not None:
            await stack.enter_async_context(_mcp_module.lifespan())

        yield

    # Stop mesh sync scheduler
    try:
        if stop_scheduler:
            stop_scheduler()
    except Exception:
        pass

    # Close shared mesh HTTP client
    try:
        from hgai_module_mesh.engine import close_http_client
        await close_http_client()
    except ImportError:
        pass

    await close_storage()
    logger.info("HypergraphAI server shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="HypergraphAI",
        description="Semantic Hypergraph Knowledge Platform API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS
    origins = settings.cors_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routers
    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(hypergraphs.router, prefix=prefix)
    app.include_router(hypernodes.router, prefix=prefix)
    app.include_router(hyperedges.router, prefix=prefix)
    app.include_router(accounts.router, prefix=prefix)
    app.include_router(spaces.router, prefix=prefix)
    app.include_router(media.router, prefix=prefix)
    app.include_router(inference.router, prefix=prefix)
    app.include_router(notes.router, prefix=prefix)
    app.include_router(parameterized_queries.router, prefix=prefix)

    # Mesh module — mounted conditionally; failures are non-fatal
    try:
        from hgai_module_mesh import MeshModule
        mesh_module = MeshModule()
        app.include_router(mesh_module.get_router(), prefix=prefix)
        logger.info("Mesh module mounted at /api/v1/meshes")
    except BaseException as e:
        logger.warning(f"Mesh module not available (continuing without it): {type(e).__name__}: {e}")

    # SHQL module — mounted conditionally; failures are non-fatal
    try:
        from hgai_module_shql import SHQLModule
        shql_module = SHQLModule()
        app.include_router(shql_module.get_router(), prefix=prefix)
        logger.info("SHQL module mounted at /api/v1/shql")
    except BaseException as e:
        logger.warning(f"SHQL module not available (continuing without it): {type(e).__name__}: {e}")

    # MCP module — mounted conditionally; failures are non-fatal
    try:
        from hgai_module_mcp import MCPModule
        global _mcp_module
        _mcp_module = MCPModule()
        app.mount("/mcp", _mcp_module.get_app())
        logger.info("MCP module mounted at /mcp")
    except BaseException as e:
        logger.warning(f"MCP module not available (continuing without it): {type(e).__name__}: {e}")

    # AI Agent Chat module — mounted conditionally; failures are non-fatal
    if settings.agent_chat_enabled:
        try:
            from hgai_module_agentchat import AgentChatModule
            agentchat_module = AgentChatModule()
            app.include_router(agentchat_module.get_router(), prefix=prefix)
            logger.info("AI Agent Chat module mounted at /api/v1/agent")
        except BaseException as e:
            logger.warning(f"AI Agent Chat module not available (continuing without it): {type(e).__name__}: {e}")

    # Serve Web UI static files
    ui_dir = Path(__file__).parent.parent / "ui"
    if ui_dir.exists():
        app.mount("/ui", NoCacheStaticFiles(directory=str(ui_dir), html=True), name="ui")

    # Health check
    @app.get("/health", tags=["system"])
    async def health():
        return {
            "status": "ok",
            "server_id": settings.server_id,
            "server_name": settings.server_name,
            "version": "0.1.0",
        }

    # Server info
    @app.get("/api/v1/server/info", tags=["system"])
    async def server_info():
        return {
            "server_id": settings.server_id,
            "server_name": settings.server_name,
            "version": "0.1.0",
            "capabilities": ["hypernodes", "hyperedges", "hypergraphs", "shql", "mcp", "mesh", "temporal", "media"],
        }

    # Root redirect to UI
    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/ui/")

    return app


app = create_app()


def cli_main():
    import argparse
    import os
    import uvicorn

    parser = argparse.ArgumentParser(description="HypergraphAI server")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on")
    parser.add_argument("--mongo-connection", "--mongo_connection", default=None, help="MongoDB connection URI (overrides HGAI_MONGO_URI)")
    parser.add_argument("--mongo-db", "--mongo_db", default=None, help="MongoDB database name (overrides HGAI_MONGO_DB)")
    parser.add_argument("--server-id", "--server_id", default=None, help="Server identifier (overrides HGAI_SERVER_ID)")
    parser.add_argument("--server-name", "--server_name", default=None, help="Server display name (overrides HGAI_SERVER_NAME)")
    args = parser.parse_args()

    # Set env vars then clear the lru_cache so get_settings() re-reads them.
    # (create_app() runs at module level and populates the cache before args are parsed.)
    if args.mongo_connection:
        os.environ["HGAI_MONGO_URI"] = args.mongo_connection
    if args.mongo_db:
        os.environ["HGAI_MONGO_DB"] = args.mongo_db
    if args.server_id:
        os.environ["HGAI_SERVER_ID"] = args.server_id
    if args.server_name:
        os.environ["HGAI_SERVER_NAME"] = args.server_name

    get_settings.cache_clear()
    settings = get_settings()

    port = (
        args.port
        or int(os.environ.get("DEFAULT_HGAI_PORT", 0))
        or settings.port
    )

    uvicorn.run(
        "hgai.main:app",
        host=settings.host,
        port=port,
        log_level=settings.log_level,
        reload=settings.reload,
    )


if __name__ == "__main__":
    cli_main()
