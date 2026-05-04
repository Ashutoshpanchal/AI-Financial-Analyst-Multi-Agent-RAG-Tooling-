from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_v1_router
from app.config.settings import get_settings
from app.core.exceptions import AppException, app_exception_handler
from app.db import models  # noqa: F401 — registers ORM models with Base
from app.db.session import Base, engine
from app.mcp.transport import mount_mcp
from app.observability.middleware import LangfuseMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / shutdown logic.
    Creates all DB tables on startup (dev-friendly alternative to migrations).
    """
    print(f"Starting AI Financial Analyst [{settings.app_env}]")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("DB tables ready.")
    yield
    print("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Financial Analyst",
        description="Multi-Agent RAG system for financial analysis",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — open in dev, restrict in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"]
        if not settings.is_production
        else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Langfuse observability — traces every request automatically
    app.add_middleware(LangfuseMiddleware)

    # Global exception handler
    app.add_exception_handler(AppException, app_exception_handler)

    # Routers
    app.include_router(api_v1_router)

    # MCP server — mounted at /mcp (SSE transport for web clients)
    mount_mcp(app)

    return app


app = create_app()
