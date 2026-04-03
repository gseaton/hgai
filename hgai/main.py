"""HypergraphAI FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager, AsyncExitStack
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from hgai.config import get_settings
from hgai.db.mongodb import connect_db, close_db
from hgai.core.auth import bootstrap_admin
from hgai.api.routers import auth, hypergraphs, hypernodes, hyperedges, accounts

logger = logging.getLogger(__name__)

_mcp_module = None  # set by create_app(), consumed by lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting HypergraphAI server: {settings.server_name} ({settings.server_id})")

    # Connect to MongoDB
    await connect_db()
    logger.info(f"Connected to MongoDB: {settings.mongo_db}")
    print(f"MongoDB database: {settings.mongo_db}")

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

    await close_db()
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

    # Mesh module — mounted conditionally; failures are non-fatal
    try:
        from hgai_module_mesh import MeshModule
        mesh_module = MeshModule()
        app.include_router(mesh_module.get_router(), prefix=prefix)
        logger.info("Mesh module mounted at /api/v1/meshes")
    except BaseException as e:
        logger.warning(f"Mesh module not available (continuing without it): {type(e).__name__}: {e}")

    # HQL module — mounted conditionally; failures are non-fatal
    try:
        from hgai_module_hql import HQLModule
        hql_module = HQLModule()
        app.include_router(hql_module.get_router(), prefix=prefix)
        logger.info("HQL module mounted at /api/v1/query")
    except BaseException as e:
        logger.warning(f"HQL module not available (continuing without it): {type(e).__name__}: {e}")

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

    # Serve Web UI static files
    ui_dir = Path(__file__).parent.parent / "ui"
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

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
            "capabilities": ["hypernodes", "hyperedges", "hypergraphs", "hql", "mcp", "mesh", "temporal"],
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
    parser.add_argument("--mongo-connection", default=None, help="MongoDB connection URI (overrides HGAI_MONGO_URI)")
    parser.add_argument("--mongo-db", default=None, help="MongoDB database name (overrides HGAI_MONGO_DB)")
    parser.add_argument("--server-id", default=None, help="Server identifier (overrides HGAI_SERVER_ID)")
    parser.add_argument("--server-name", default=None, help="Server display name (overrides HGAI_SERVER_NAME)")
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
