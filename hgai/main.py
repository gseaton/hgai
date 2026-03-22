"""HypergraphAI FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from hgai.config import get_settings
from hgai.db.mongodb import connect_db, close_db
from hgai.core.auth import bootstrap_admin
from hgai.api.routers import auth, hypergraphs, hypernodes, hyperedges, query, accounts, meshes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting HypergraphAI server: {settings.server_name} ({settings.server_id})")

    # Connect to MongoDB
    await connect_db()
    logger.info(f"Connected to MongoDB: {settings.mongo_db}")

    # Bootstrap admin account on first run
    created = await bootstrap_admin(
        username=settings.admin_username,
        password=settings.admin_password,
        email=settings.admin_email,
    )
    if created:
        logger.info(f"Admin account '{settings.admin_username}' created (first run bootstrap)")

    yield

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
    app.include_router(query.router, prefix=prefix)
    app.include_router(accounts.router, prefix=prefix)
    app.include_router(meshes.router, prefix=prefix)

    # MCP server — mounted conditionally; failures are non-fatal
    try:
        from hgai.mcp.server import create_mcp_server
        mcp_app = create_mcp_server()
        app.mount("/mcp", mcp_app)
        logger.info("MCP server mounted at /mcp")
    except BaseException as e:
        logger.warning(f"MCP server not available (continuing without it): {type(e).__name__}: {e}")

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
            "capabilities": ["hypernodes", "hyperedges", "hypergraphs", "hql", "mcp", "mesh", "temporal", "inference"],
        }

    # Root redirect to UI
    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/ui/")

    return app


app = create_app()


def cli_main():
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "hgai.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=settings.reload,
    )


if __name__ == "__main__":
    cli_main()
