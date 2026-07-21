"""FastAPI application for AI Content OS"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_config
from backend.db.models import init_db, create_tables
from backend.db.migrations import run_migrations
from backend.api.middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    init_db()
    create_tables()
    try:
        run_migrations()
    except Exception as e:
        logger.warning(f"Alembic migrations skipped: {e}")
    logger.info(f"AI Content OS v{config.version} started")
    yield
    logger.info("AI Content OS shutting down")


def create_app() -> FastAPI:
    config = get_config()

    app = FastAPI(
        title=config.name,
        version=config.version,
        description=(
            "AI Content Operating System - A multi-agent platform for content creation, "
            "SEO optimization, video generation, and content management. "
            "Features 8 specialized AI agents, visual workflow builder, "
            "brand consistency engine, RAG-powered research, and real-time collaboration."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "auth", "description": "User registration, login, and API key management"},
            {"name": "chat", "description": "AI chat with streaming support"},
            {"name": "models", "description": "AI model routing and cost estimation"},
            {"name": "agents", "description": "Multi-agent system with 8 specialized agents"},
            {"name": "content", "description": "Content lifecycle management"},
            {"name": "projects", "description": "Project organization and management"},
            {"name": "brands", "description": "Brand identity and consistency"},
            {"name": "workflows", "description": "Visual workflow orchestration"},
            {"name": "memory", "description": "Long-term memory and context"},
            {"name": "analytics", "description": "Usage analytics and cost tracking"},
            {"name": "plugins", "description": "Plugin marketplace and management"},
            {"name": "video", "description": "Video generation pipeline"},
            {"name": "rag", "description": "RAG-powered research and knowledge base"},
            {"name": "admin", "description": "Admin-only system management"},
            {"name": "webhooks", "description": "Event webhook management"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)

    from backend.api.routes import router
    app.include_router(router, prefix="/api/v1")

    from backend.api.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/v1")

    from backend.api.webhooks import router as webhook_router
    app.include_router(webhook_router, prefix="/api/v1")

    from backend.api.websocket import websocket_router
    app.include_router(websocket_router)

    @app.get("/health")
    def health_check():
        return {"status": "healthy", "version": config.version}

    return app


app = create_app()
